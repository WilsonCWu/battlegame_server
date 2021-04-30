import math
import random
from datetime import timedelta, datetime, timezone

from django.db import transaction
from django.db.models import Model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_marshmallow import Schema, fields

from playerdata import constants, formulas, rolls
from playerdata.constants import ChestType
from playerdata.models import Chest, BaseItem, Item, UserInfo, DailyDungeonStatus
from playerdata.questupdater import QuestUpdater
from playerdata.serializers import ValueSerializer, CollectChestSerializer


# Examples:
# 'gems', 100
# 'char_id', 12
# 'item_id', 1001
# 'coins', 10000
class ChestRewardSchema(Schema):
    reward_type = fields.Str()
    value = fields.Int()


class ChestReward:
  def __init__(self, reward_type, value):
    self.reward_type = reward_type
    self.value = value


def chest_unlock_timedelta(rarity: int):
    if rarity == ChestType.SILVER.value:
        hours = 3
    elif rarity == ChestType.GOLD.value:
        hours = 8
    elif rarity == ChestType.MYTHICAL.value:
        hours = 12
    elif rarity == ChestType.EPIC.value:
        hours = 12
    else:  # Max / Legendary
        hours = 24

    return timedelta(hours=hours)


def skip_cost(chest: Chest):
    # we charge full price if you're skipping without unlocking baby
    if chest.locked_until is None:
        return constants.CHEST_GEMS_PER_HOUR * chest_unlock_timedelta(chest.rarity).total_seconds() / 3600
    curr_time = datetime.now(timezone.utc)
    remaining_seconds = (chest.locked_until - curr_time).total_seconds()
    return max(1, math.floor(constants.CHEST_GEMS_PER_HOUR * remaining_seconds / 3600))


class UnlockChest(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chest_id = serializer.validated_data['value']

        my_chest = None
        chests = Chest.objects.filter(user=request.user)
        curr_time = datetime.now(timezone.utc)

        for chest in chests:
            if chest.locked_until is not None and chest.locked_until > curr_time:
                return Response({'status': False, 'reason': 'can only unlock 1 chest at a time'})

            if chest.id == int(chest_id):
                my_chest = chest

        if my_chest is None:
            return Response({'status': False, 'reason': 'chest_id does not exist ' + chest_id})

        unlock_time = datetime.now(timezone.utc) + chest_unlock_timedelta(my_chest.rarity)

        my_chest.locked_until = unlock_time
        my_chest.save()

        return Response({'status': True, 'locked_until': unlock_time})


def give_some_pity(user, rewards, chest_type: int):
    # if no legendaries increment the pity counters per chest
    # if there are, reset the counter
    if chest_type == constants.ChestType.MYTHICAL.value:
        pity_counter = user.userstats.mythic_pity_counter
        pity_attr = 'mythic_pity_counter'
        pity_cap = constants.LEGENDARY_PITY_CAP_MYTHICAL
    # elif chest_type == constants.ChestType.SILVER.value:
    #     pity_counter = user.userstats.silver_pity_counter
    #     pity_attr = 'silver_pity_counter'
    #     pity_cap = constants.LEGENDARY_PITY_CAP_SILVER
    # elif chest_type == constants.ChestType.GOLD.value:
    #     pity_counter = user.userstats.gold_pity_counter
    #     pity_attr = 'gold_pity_counter'
    #     pity_cap = constants.LEGENDARY_PITY_CAP_GOLD
    else:
        # otherwise we don't count pity for this type of chest
        return rewards

    for reward in rewards:
        if reward.reward_type == 'char_id':
            if constants.is_legendary(reward.value):
                pity_counter = 0
            else:
                pity_counter += 1
                if pity_counter >= pity_cap:
                    reward.value = random.choice(constants.LEGENDARY_CHAR_IDS)
                    pity_counter = 0

    setattr(user.userstats, pity_attr, pity_counter)
    user.userstats.save()
    return rewards


def pick_resource_reward(user, resource_type, chest_rarity, chest_tier=None):
    if chest_tier is None:
        chest_tier = user.userinfo.tier_rank

    if resource_type == 'coins':
        pivot_amount = formulas.coins_chest_reward(user, chest_rarity, chest_tier)
    elif resource_type == 'gems':
        pivot_amount = formulas.gems_chest_reward(chest_rarity)
    else:
        pivot_amount = formulas.dust_chest_reward(user, chest_rarity, chest_tier)

    # randomly draw from within +/- 15% of that pivot_amount
    amount = random.randint(math.floor(0.85 * pivot_amount), math.floor(pivot_amount * 1.15))
    return ChestReward(reward_type=resource_type, value=amount)


# randomly pick item from rarity buckets
def pick_reward_item(user, chest_rarity):
    rarity_odds = constants.REGULAR_ITEM_ODDS_PER_CHEST[chest_rarity - 1]
    item = rolls.get_weighted_odds_item(rarity_odds)

    # check for unique items
    if item.is_unique and Item.objects.filter(user=user, item_type=item).exists():
        item = rolls.get_weighted_odds_item(rarity_odds)

        # we'll just give them a char if we roll a dup unique item twice
        if item.is_unique and Item.objects.filter(user=user, item_type=item).exists():
            return pick_reward_char(chest_rarity)

    return ChestReward(reward_type='item_id', value=item.item_type)


# randomly pick char from rarity buckets
def pick_reward_char(chest_rarity):
    rarity_odds = constants.REGULAR_CHAR_ODDS_PER_CHEST[chest_rarity - 1]
    char_id = rolls.get_weighted_odds_character(rarity_odds).char_type
    return ChestReward(reward_type='char_id', value=char_id)


def roll_guaranteed_char_rewards(char_guarantees):
    rewards = []
    # for each char rarity
    for i in range(len(char_guarantees)):
        # roll that many guaranteed chars
        for j in range(char_guarantees[i]):
            char_id = rolls.get_rand_base_char_from_rarity(i + 1).char_type
            char_reward = ChestReward(reward_type='char_id', value=char_id)
            rewards.append(char_reward)
    return rewards


def award_chest_rewards(user, rewards):
    for reward in rewards:
        if reward.reward_type == 'coins':
            user.inventory.coins += reward.value
        elif reward.reward_type == 'gems':
            user.inventory.gems += reward.value
        elif reward.reward_type == 'essence':
            user.inventory.dust += reward.value
        elif reward.reward_type == 'char_id':
            rolls.insert_character(user, reward.value)
        elif reward.reward_type == 'item_id':
            base_item = BaseItem.objects.get(item_type=reward.value)
            if not base_item.is_unique:
                Item.objects.create(user=user, item_type=base_item)
        elif reward.reward_type == 'profile_pic':
            if user.inventory.profile_pics is None:
                user.inventory.profile_pics = [reward.value]
            else:
                user.inventory.profile_pics.append(reward.value)
        else:
            raise Exception("invalid reward_type, sorry friendo")
    user.inventory.save()
    QuestUpdater.add_progress_by_type(user, constants.CHESTS_OPENED, 1)


def get_guaranteed_chars_rarity_odds(chest_rarity: int, user):
    if chest_rarity == constants.ChestType.DAILY_DUNGEON.value:
        dd_status = DailyDungeonStatus.get_active_for_user(user)

        # guarantee an epic if finishing stage >60
        # otherwise a rare
        if dd_status.stage >= 80:
            char_guarantees = [0, 3, 1, 0]
        elif dd_status.stage >= 70:
            char_guarantees = [0, 2, 1, 0]
        elif dd_status.stage >= 60:
            char_guarantees = [0, 1, 1, 0]
        elif dd_status.stage >= 50:
            char_guarantees = [0, 2, 0, 0]
        elif dd_status.stage >= 40:
            char_guarantees = [0, 2, 0, 0]
        elif dd_status.stage >= 30:
            char_guarantees = [0, 1, 0, 0]
        elif dd_status.stage >= 20:
            char_guarantees = [0, 1, 0, 0]
        else:
            char_guarantees = [0, 1, 0, 0]

    else:
        char_guarantees = constants.GUARANTEED_CHARS_PER_RARITY_PER_CHEST[chest_rarity - 1]

    return char_guarantees


def generate_chest_rewards(chest_rarity: int, user, chest_tier=None):
    if chest_tier is None:
        chest_tier = user.userinfo.tier_rank

    rewards = []
    num_rewards = random.randint(constants.MIN_REWARDS_PER_CHEST[chest_rarity - 1],
                                 constants.MAX_REWARDS_PER_CHEST[chest_rarity - 1])

    # Get the odds for getting each type of reward for respective chest rarity
    resource_reward_odds = constants.RESOURCE_TYPE_ODDS_PER_CHEST[chest_rarity - 1]

    # guarantee a coin and dust drop in any chest
    rewards.append(pick_resource_reward(user, 'coins', chest_rarity, chest_tier))
    rewards.append(pick_resource_reward(user, 'essence', chest_rarity, chest_tier))
    num_rewards -= 2

    # pick guaranteed char rarities
    char_guarantees = get_guaranteed_chars_rarity_odds(chest_rarity, user)
    guaranteed_char_rewards = roll_guaranteed_char_rewards(char_guarantees)
    rewards.extend(guaranteed_char_rewards)
    num_rewards -= len(guaranteed_char_rewards)

    # pick guaranteed number of summons
    num_guaranteed_summons = constants.GUARANTEED_SUMMONS[chest_rarity - 1] - len(guaranteed_char_rewards)
    for i in range(0, num_guaranteed_summons):
        reward = pick_reward_char(chest_rarity)
        rewards.append(reward)
    num_rewards -= num_guaranteed_summons

    # roll the rest of the rewards based on resource_reward_odds
    for i in range(0, num_rewards):
        rand_reward_type = constants.REWARD_TYPE_INDEX[rolls.weighted_pick_from_buckets(resource_reward_odds)]
        if rand_reward_type in ['coins', 'gems', 'essence']:
            reward = pick_resource_reward(user, rand_reward_type, chest_rarity, chest_tier)
        elif rand_reward_type == 'item_id':
            reward = pick_reward_item(user, chest_rarity)
        elif rand_reward_type == 'char_id':
            reward = pick_reward_char(chest_rarity)
        else:
            raise Exception("invalid reward_type, sorry friendo")

        rewards.append(reward)

    rewards = give_some_pity(user, rewards, chest_rarity)
    return rewards


class CollectChest(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = CollectChestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chest_id = serializer.validated_data['chest_id']
        is_skip = serializer.validated_data['is_skip']

        try:
            chest = Chest.objects.get(user=request.user, id=chest_id)
        except Chest.DoesNotExist:
            return Response({'status': False, 'reason': 'chest_id does not exist %d' % chest_id})

        if chest.locked_until is None and not is_skip:
            return Response({'status': False, 'reason': 'chest needs to be unlocked first'})

        inventory = request.user.inventory

        if is_skip:
            gems_cost = skip_cost(chest)
            if inventory.gems < gems_cost:
                return Response({'status': False, 'reason': 'not enough gems to skip'})
            inventory.gems -= gems_cost
            inventory.save()
        else:
            if datetime.now(timezone.utc) < chest.locked_until:
                return Response({'status': False, 'reason': 'chest is not ready to open'})

        rewards = generate_chest_rewards(chest.rarity, request.user)
        award_chest_rewards(request.user, rewards)
        chest.delete()

        reward_schema = ChestRewardSchema(rewards, many=True)
        return Response({'status': True, 'rewards': reward_schema.data})
