import math
import random
from datetime import timedelta, datetime, timezone

from django.db.models import Model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_marshmallow import Schema, fields

from playerdata import constants, formulas
from playerdata.constants import ChestType
from playerdata.models import Chest
from playerdata.serializers import ValueSerializer, CollectChestSerializer


class ChestSchema(Schema):
    user_id = fields.Int(attribute='user.id')
    rarity = fields.Int()
    locked_until = fields.DateTime()


# Examples:
# "gems", 100
# char_id, 12
# item_id, 1001
# coins, 10000
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
    else: # Max / Legendary
        hours = 24

    return timedelta(hours=hours)


def skip_cost(rarity: int):
    return constants.CHEST_GEMS_PER_HOUR * chest_unlock_timedelta(rarity).total_seconds() / 3600


class ChestView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        chests = Chest.objects.filter(user=request.user)
        chest_schema = ChestSchema(chests, many=True)
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

        Response({'status': True})


def get_rand_from_bucket(buckets):
    rand = random.randint(1, 100)
    total = 0
    for i, bucket in enumerate(buckets):
        total += bucket
        if rand < total:
            return i

    # should never hit this
    return -1


def reward_resource(user, resource_type, rarity):
    # random range
    # scale off of elo
    if resource_type == 'coins':
        pivot_amount = formulas.coins_chest_reward(user.dungeonprogress.stage_id, rarity)
    elif resource_type == 'gems':
        pivot_amount = formulas.gems_chest_reward(user.dungeonprogress.stage_id, rarity)
    else:
        pivot_amount = formulas.essence_chest_reward(user.dungeonprogress.stage_id, rarity)

    # randomly draw from within +/- 15% of that amount
    amount = random.randint(math.floor(0.85 * pivot_amount), math.floor(pivot_amount * 1.15))
    return ChestReward(reward_type=resource_type, value=amount)


class CollectChest(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = CollectChestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        chest_id = serializer.validated_data['chest_id']
        is_skip = serializer.validated_data['is_skip']

        try:
            chest = Chest.objects.get(id=chest_id)
        except Model.DoesNotExist as e:
            return Response({'status': False, 'reason': 'chest_id does not exist ' + chest_id})

        inventory = request.user.inventory

        if is_skip:
            if inventory.gems < skip_cost(chest.rarity):
                return Response({'status': False, 'reason': 'not enough gems to skip'})
            inventory.gems -= skip_cost(chest.rarity)
        else:
            if chest.locked_until is None or datetime.now(timezone.utc) < chest.locked_until:
                return Response({'status': False, 'reason': 'chest is not ready to open'})

        # open chest based on rarity
        # pick based on rarity the types of rewards
        # dust gems coins items characters

        """
        dust: scaled to elo range
        gems: scaled to elo range
        coins: scaled to elo range
        
        chars: guarantee 
        
        return [ {
            "type": "gems" / "coins" / "char"
            "value": 100 / 100 / 14 (char_id)
        } ] 
        
        buckets
        
        
        
        """
        rewards = []
        num_rewards = random.randint(5, 10)

        if chest.rarity == constants.ChestType.SILVER:
            resource_reward_odds = [10, 10, 10, 50, 20]
        elif chest.rarity == constants.ChestType.GOLD:
            resource_reward_odds = [10, 10, 10, 50, 20]
        elif chest.rarity == constants.ChestType.MYTHICAL:
            resource_reward_odds = [10, 10, 10, 50, 20]
        elif chest.rarity == constants.ChestType.EPIC:
            resource_reward_odds = [10, 10, 10, 50, 20]
        else:  # constants.ChestType.LEGENDARY
            resource_reward_odds = [10, 10, 10, 40, 30]

        for i in range(0, num_rewards):
            rand_reward_type = constants.REWARD_TYPE_INDEX[get_rand_from_bucket(resource_reward_odds)]
            if rand_reward_type == 'coins' or rand_reward_type == 'gems' or rand_reward_type == 'essence':
                reward = reward_resource(request.user, rand_reward_type, chest.rarity)
            elif rand_reward_type == 'item_id':
                # reward = reward_item()
                pass
            else:
                # reward = reward_char()
                pass

            rewards.append(reward)

        reward_schema = ChestRewardSchema(rewards, many=True)
        return Response({'status': True, 'rewards': reward_schema.data})
