import math
import random
from datetime import timedelta, datetime, timezone

from django.db import transaction
from django.db.models import Model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_marshmallow import Schema, fields

from playerdata import constants, formulas
from playerdata.constants import ChestType
from playerdata.models import Chest, BaseItem, Item, UserInfo
from playerdata.purchases import get_rand_base_char_from_rarity, get_weighted_odds_character, get_weighted_odds_item, \
    insert_character, weighted_pick_from_buckets
from playerdata.serializers import ValueSerializer, CollectChestSerializer


class ChestSchema(Schema):
    user_id = fields.Int(attribute='user.id')
    rarity = fields.Int()
    locked_until = fields.DateTime()


class ChestSlotsSchema(Schema):
    chest_slot_1 = fields.Nested(ChestSchema)
    chest_slot_2 = fields.Nested(ChestSchema)
    chest_slot_3 = fields.Nested(ChestSchema)
    chest_slot_4 = fields.Nested(ChestSchema)


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


def skip_cost(unlock_time: datetime):
    curr_time = datetime.now(timezone.utc)
    remaining_seconds = (unlock_time - curr_time).total_seconds()
    return max(1, math.floor(constants.CHEST_GEMS_PER_HOUR * remaining_seconds / 3600))


class ChestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        chest_schema = ChestSlotsSchema(request.user.inventory)
        return Response({chest_schema.data})


class UnlockChest(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chest_id = serializer.validated_data['value']

        try:
            chest = Chest.objects.get(id=chest_id)
        except Model.DoesNotExist as e:
            return Response({'status': False, 'reason': 'chest_id does not exist ' + chest_id})

        unlock_time = datetime.now(timezone.utc) + chest_unlock_timedelta(chest.rarity)

        chest.locked_until = unlock_time
        chest.save()

        return Response({'status': True})


def reward_resource(user, resource_type, chest_rarity):
    # scale off of elo
    userinfo = UserInfo.objects.get(user=user)

    if resource_type == 'coins':
        pivot_amount = formulas.coins_chest_reward(userinfo.elo, chest_rarity)
    elif resource_type == 'gems':
        pivot_amount = formulas.gems_chest_reward(userinfo.elo, chest_rarity)
    else:
        pivot_amount = formulas.essence_chest_reward(userinfo.elo, chest_rarity)

    # randomly draw from within +/- 15% of that pivot_amount
    amount = random.randint(math.floor(0.85 * pivot_amount), math.floor(pivot_amount * 1.15))
    return ChestReward(reward_type=resource_type, value=amount)


# randomly pick item from rarity buckets
def pick_reward_item(chest_rarity):
    rarity_odds = constants.REGULAR_ITEM_ODDS_PER_CHEST[chest_rarity - 1]
    item_id = get_weighted_odds_item(rarity_odds).item_type
    return ChestReward(reward_type='item_id', value=item_id)


# randomly pick char from rarity buckets
def pick_reward_char(chest_rarity):
    rarity_odds = constants.REGULAR_CHAR_ODDS_PER_CHEST[chest_rarity - 1]
    char_id = get_weighted_odds_character(rarity_odds).char_type # todo: odds are out of 100, change to cumulative
    return ChestReward(reward_type='char_id', value=char_id)


def roll_guaranteed_char_rewards(char_guarantees):
    rewards = []
    i = 0
    while i < len(char_guarantees):
        # roll a guaranteed rarity char
        if char_guarantees[i] > 0:
            char_id = get_rand_base_char_from_rarity(i + 1).char_type
            char_reward = ChestReward(reward_type='char_id', value=char_id)
            rewards.append(char_reward)

            char_guarantees[i] -= 1

        if char_guarantees[i] == 0:
            i += 1

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
            insert_character(user, reward.value)
        else:
            base_item = BaseItem.objects.get(item_type=reward.value)
            if not base_item.is_unique:
                Item.objects.create(user=user, item_type=base_item)


class CollectChest(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = CollectChestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chest_id = serializer.validated_data['chest_id']
        is_skip = serializer.validated_data['is_skip']

        try:
            chest = Chest.objects.get(id=chest_id)
        except Model.DoesNotExist as e:
            return Response({'status': False, 'reason': 'chest_id does not exist ' + chest_id})

        if chest.locked_until is None:
            return Response({'status': False, 'reason': 'chest needs to be unlocked first'})

        inventory = request.user.inventory

        if is_skip:
            gems_cost = skip_cost(chest.locked_until)
            if inventory.gems < gems_cost:
                return Response({'status': False, 'reason': 'not enough gems to skip'})
            inventory.gems -= gems_cost
            inventory.save()
        else:
            if datetime.now(timezone.utc) < chest.locked_until:
                return Response({'status': False, 'reason': 'chest is not ready to open'})

        rewards = []
        num_rewards = random.randint(constants.MIN_REWARDS_PER_CHEST[chest.rarity - 1],
                                     constants.MAX_REWARDS_PER_CHEST[chest.rarity - 1])

        # Get the odds for getting each type of reward for respective chest rarity
        resource_reward_odds = constants.RESOURCE_TYPE_ODDS_PER_CHEST[chest.rarity - 1]

        # first pick guaranteed chars
        char_guarantees = constants.GUARANTEED_CHARS_PER_RARITY_PER_CHEST[chest.rarity - 1]
        guaranteed_char_rewards = roll_guaranteed_char_rewards(char_guarantees)
        rewards.extend(guaranteed_char_rewards)
        num_rewards -= len(guaranteed_char_rewards)

        # roll the rest of the rewards based on resource_reward_odds
        for i in range(0, num_rewards):
            rand_reward_type = constants.REWARD_TYPE_INDEX[weighted_pick_from_buckets(resource_reward_odds)]
            if rand_reward_type == 'coins' or rand_reward_type == 'gems' or rand_reward_type == 'essence':
                reward = reward_resource(request.user, rand_reward_type, chest.rarity)
            elif rand_reward_type == 'item_id':
                reward = pick_reward_item(chest.rarity)
            else:
                reward = pick_reward_char(chest.rarity)

            rewards.append(reward)

        # award chest rewards
        award_chest_rewards(request.user, rewards)

        reward_schema = ChestRewardSchema(rewards, many=True)
        return Response({'status': True, 'rewards': reward_schema.data})
