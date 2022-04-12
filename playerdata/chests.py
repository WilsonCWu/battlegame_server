import math
import random
from datetime import timedelta, datetime, timezone, date

from cachetools.func import lru_cache
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import constants, formulas, rolls, tier_system, base, server
from playerdata.constants import ChestType
from playerdata.models import Chest, BaseItem, Item, DailyDungeonStatus, BaseCharacter
from playerdata.questupdater import QuestUpdater
from playerdata.serializers import ValueSerializer, CollectChestSerializer, IntSerializer


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

    def __str__(self):
        return f"<reward_type {self.reward_type}: {self.value}>"

    def __repr__(self):
        return f"<reward_type {self.reward_type}: {self.value} value: {int(self.gem_value())}>"

    def gem_value(self):
        # fast rewards are based off of cost for 2 hrs in afk arena
        if self.reward_type == constants.RewardType.COINS_FAST_REWARDS.value:
            return self.value * 38
        elif self.reward_type == constants.RewardType.DUST_FAST_REWARDS.value:
            return self.value * 50  # vague estimate, more valuable late game, not so much early
        elif self.reward_type == constants.RewardType.GEMS.value:
            return self.value

        # shard values are based off of mythical chest
        elif self.reward_type == constants.RewardType.RARE_SHARDS.value:
            return (self.value / 80) * 438
        elif self.reward_type == constants.RewardType.EPIC_SHARDS.value:
            return (self.value / 80) * 1687
        elif self.reward_type == constants.RewardType.LEGENDARY_SHARDS.value:
            return (self.value / 80) * 11250
        elif self.reward_type == constants.RewardType.RELIC_STONES.value:
            return (self.value / 600) * 1687  # valued off of relic stones cost for an epic
        else:
            return 0


# This corresponds to ChestRewardsList on client
def chestRewardsList_to_json(rewards_list):
    rewards_json = []

    for rewards in rewards_list:
        rewards_json.append({'rewards': ChestRewardSchema(rewards, many=True).data})

    return rewards_json


def chest_unlock_timedelta(rarity: int):
    if rarity == ChestType.SILVER.value:
        hours = 3
    elif rarity == ChestType.GOLD.value:
        hours = 8
    elif rarity == ChestType.MYTHICAL.value:
        hours = 12
    elif rarity == ChestType.EPIC.value:
        hours = 12
    elif rarity == ChestType.LOGIN_GEMS.value:
        hours = 22
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

    @transaction.atomic
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
    else:
        # otherwise we don't count pity for this type of chest
        return rewards

    for reward in rewards:
        if reward.reward_type == 'char_id':
            # If a legendary is rolled we reset the pity
            if base.get_char_rarity(reward.value) == 4:
                pity_counter = 0
            else:
                pity_counter += 1
                if pity_counter >= pity_cap:
                    legendaries = list(BaseCharacter.objects.filter(rollable=True, rarity=4).values_list('char_type', flat=True))
                    reward.value = random.choice(legendaries)
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
            return pick_reward_char(user, chest_rarity)

    return ChestReward(reward_type='item_id', value=item.item_type)


# randomly pick char from rarity buckets
def pick_reward_char(user, chest_rarity):
    rarity_odds = constants.REGULAR_CHAR_ODDS_PER_CHEST[chest_rarity - 1]
    char_id = rolls.get_weighted_odds_character(rarity_odds).char_type
    if user.wishlist.is_active:
        char_id = rolls.get_wishlist_odds_char_type(user.wishlist, rarity_odds)

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
        elif reward.reward_type == 'relic_stone':
            user.inventory.relic_stones += reward.value
        elif reward.reward_type == 'rare_shards':
            user.inventory.rare_shards += reward.value
        elif reward.reward_type == 'epic_shards':
            user.inventory.epic_shards += reward.value
        elif reward.reward_type == 'legendary_shards':
            user.inventory.legendary_shards += reward.value
        elif reward.reward_type == 'dust_fast_reward_hours':
            user.inventory.dust_fast_reward_hours += reward.value
        elif reward.reward_type == 'coins_fast_reward_hours':
            user.inventory.coins_fast_reward_hours += reward.value
        elif reward.reward_type == 'ember':
            user.inventory.ember += reward.value
        elif reward.reward_type == 'champ_badge':
            user.inventory.champ_badges += reward.value
            tier_system.complete_any_champ_rewards(user.inventory.champ_badges, user.champbadgetracker)
        elif reward.reward_type == 'regal_points':
            user.regalrewards.points += reward.value
            user.regalrewards.save()
        elif reward.reward_type == 'char_id':
            rolls.insert_character(user, reward.value)
        elif reward.reward_type == 'item_id':
            base_item = BaseItem.objects.get(item_type=reward.value)
            if not base_item.is_unique:
                Item.objects.create(user=user, item_type=base_item)
        elif reward.reward_type == 'profile_pic':
            if user.inventory.profile_pics is None:
                user.inventory.profile_pics = [reward.value]
            elif reward.value not in user.inventory.profile_pics:
                user.inventory.profile_pics.append(reward.value)
        elif reward.reward_type == 'pet_id':
            user.inventory.pets_unlocked.append(reward.value)
        else:
            raise Exception("invalid reward_type, sorry friendo")
    user.inventory.save()


# guarantee a coin and dust drop in chests
def guarantee_resources(rewards, num_rewards, chest_rarity: int, user, chest_tier):
    if chest_rarity != constants.ChestType.LEGENDARY.value:
        rewards.append(pick_resource_reward(user, 'coins', chest_rarity, chest_tier))
        rewards.append(pick_resource_reward(user, 'essence', chest_rarity, chest_tier))
        num_rewards -= 2
    return rewards, num_rewards


def get_guaranteed_summons(chest_rarity: int, guaranteed_char_rewards, user):
    num_guaranteed_summons = constants.GUARANTEED_SUMMONS[chest_rarity - 1] - len(guaranteed_char_rewards)

    # Increase num summons based on stage if DailyDungeon
    if chest_rarity == constants.ChestType.DAILY_DUNGEON.value:
        dd_status = DailyDungeonStatus.get_active_for_user(user)

        if dd_status.stage >= 60:
            num_guaranteed_summons += 2
        elif dd_status.stage >= 40:
            num_guaranteed_summons += 1

    return num_guaranteed_summons


def generate_chest_rewards(chest_rarity: int, user, chest_tier=None):
    if chest_tier is None:
        chest_tier = user.userinfo.tier_rank

    rewards = []
    num_rewards = random.randint(constants.MIN_REWARDS_PER_CHEST[chest_rarity - 1],
                                 constants.MAX_REWARDS_PER_CHEST[chest_rarity - 1])

    # Get the odds for getting each type of reward for respective chest rarity
    resource_reward_odds = constants.RESOURCE_TYPE_ODDS_PER_CHEST[chest_rarity - 1]
    rewards, num_rewards = guarantee_resources(rewards, num_rewards, chest_rarity, user, chest_tier)

    # TODO(daniel): this should go after we guarantee number of summons,
    #  and only if guaranteed rarity wasn't rolled do we roll one
    # pick guaranteed char rarities
    char_guarantees = constants.GUARANTEED_CHARS_PER_RARITY_PER_CHEST[chest_rarity - 1]
    guaranteed_char_rewards = roll_guaranteed_char_rewards(char_guarantees)
    rewards.extend(guaranteed_char_rewards)
    num_rewards -= len(guaranteed_char_rewards)

    # pick guaranteed number of summons
    num_guaranteed_summons = get_guaranteed_summons(chest_rarity, guaranteed_char_rewards, user)
    for i in range(0, num_guaranteed_summons):
        reward = pick_reward_char(user, chest_rarity)
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
            reward = pick_reward_char(user, chest_rarity)
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

        if chest.rarity == constants.ChestType.LOGIN_GEMS.value:
            gems = rolls.login_chest_gems()
            rewards = [ChestReward('gems', gems)]
            chest.locked_until = datetime.now(timezone.utc) + chest_unlock_timedelta(constants.ChestType.LOGIN_GEMS.value)
            award_chest_rewards(request.user, rewards)
            chest.save()
        else:
            rewards = generate_chest_rewards(chest.rarity, request.user, chest.tier_rank)
            award_chest_rewards(request.user, rewards)
            chest.delete()

        QuestUpdater.add_progress_by_type(request.user, constants.CHESTS_OPENED, 1)

        reward_schema = ChestRewardSchema(rewards, many=True)
        return Response({'status': True, 'rewards': reward_schema.data})


class QueueChestView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chest_id = serializer.validated_data['value']

        if not request.user.userinfo.is_monthly_sub:
            return Response({'status': False, 'reason': 'Please purchase Battle Pass to unlock this feature'})

        queued_chest = None
        chests = list(Chest.objects.filter(user=request.user).order_by('locked_until'))

        if chests[0].locked_until is None:
            return Response({'status': False, 'reason': 'cannot queue chest, no other chests unlocking'})

        num_chests_queued = 0
        for chest in chests:
            if chest.id == chest_id:
                chest.locked_until = datetime.now(timezone.utc)  # placeholder until it is set later
                queued_chest = chest

            if chest.locked_until is not None:
                num_chests_queued += 1

        if queued_chest is None:
            return Response({'status': False, 'reason': 'chest_id does not exist ' + chest_id})

        # reinsert the chest at the end of queue
        index_to_insert = num_chests_queued - 1
        chests.remove(queued_chest)
        chests.insert(index_to_insert, queued_chest)

        # reorder the queue timers
        for i, chest in enumerate(chests):
            if i == 0:
                continue
            if chest.locked_until is not None or chest.id == chest_id:
                chest.locked_until = chests[i - 1].locked_until + chest_unlock_timedelta(chest.rarity)

        Chest.objects.bulk_update(chests, ['locked_until'])
        return Response({'status': True})


@lru_cache()
def get_daily_fortune_cards(ordinal_date: int):
    rng = random.Random(ordinal_date)

    rares = list(BaseCharacter.objects.filter(rarity=2, rollable=True).values_list('char_type', flat=True))
    epics = list(BaseCharacter.objects.filter(rarity=3, rollable=True).values_list('char_type', flat=True))
    legs = list(BaseCharacter.objects.filter(rarity=4, rollable=True).values_list('char_type', flat=True))

    rare_char = rng.choice(rares)
    epic_char = rng.choice(epics)
    leg_char = rng.choice(legs)

    return [rare_char, epic_char, leg_char]


class GetFortuneChestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        seed_int = date.today().toordinal()

        return Response({
            'status': True,
            'char_ids': get_daily_fortune_cards(seed_int)
        })
