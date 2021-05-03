import math
from typing import List
from functools import lru_cache

from django.contrib.auth.models import User
from marshmallow import fields
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema

from playerdata import constants, chests
from playerdata.models import EloRewardTracker
from playerdata.serializers import IntSerializer


# Examples:
# {'gems', 1, 50, 100}
# {'char_id', 1, 100, 12}
# {'item_id', 1, 150, 1001}
# {'coins', 1, 200, 10000}
# {'chest', 1, 250, 1 (rarity)}
class EloRewardSchema(Schema):
    id = fields.Int()
    elo = fields.Int()
    reward_type = fields.Str()
    value = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()


class EloReward:
    def __init__(self, reward_id, elo, reward_type, value):
        self.id = reward_id
        self.elo = elo
        self.reward_type = reward_type
        self.value = value


def elo_to_tier(elo: int):
    if elo < constants.Tiers.MASTER.value * constants.TIER_ELO_INCREMENT:
        return constants.Tiers(math.floor(elo / constants.TIER_ELO_INCREMENT) + 1)
    else:
        return constants.Tiers.MASTER


#  we peg the rewards to the middle elo of each tier
#  Ex: If you're at Bronze 4 (100-199 elo), the rewards are pegged at 150 elo
def get_tier_reward_elo(tier: int):
    return (tier * constants.TIER_ELO_INCREMENT) - constants.TIER_ELO_INCREMENT / 2


# can change to regular @cache if we upgrade python 3.9
@lru_cache()
def get_elo_rewards_list() -> List[EloReward]:
    rewards = []
    last_reward_elo = constants.Tiers.MASTER.value * constants.TIER_ELO_INCREMENT

    reward_id = 0
    for elo in range(50, last_reward_elo, 50):
        if elo % 500 == 0:
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.MYTHICAL.value))
        elif elo % 250 == 0:
            rewards.append(EloReward(reward_id, elo, 'gems', 500))
        elif elo % 200 == 0:
            rewards.append(EloReward(reward_id, elo, 'dust', 100 * elo_to_tier(elo).value))
        elif elo % 150 == 0:
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.GOLD.value))
        elif elo % 100 == 0:
            rewards.append(EloReward(reward_id, elo, 'coins', 500 * elo_to_tier(elo).value))
        elif elo % 50 == 0:
            rewards.append(EloReward(reward_id, elo, 'chest', constants.ChestType.SILVER.value))

        reward_id += 1

    return rewards


# returns a List[ChestReward]
def convert_elo_reward_to_chest_reward(elo_reward: EloReward, user: User):
    if elo_reward.reward_type == 'chest':
        return chests.generate_chest_rewards(elo_reward.value, user)
    else:
        return [chests.ChestReward(elo_reward.reward_type, elo_reward.value)]


class GetEloRewardListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):

        elo_rewards = get_elo_rewards_list()
        rewards_data = EloRewardSchema(elo_rewards, many=True).data

        for reward in rewards_data:
            reward['claimed'] = reward['id'] in request.user.elorewardtracker.claimed
            reward['completed'] = reward['id'] in request.user.elorewardtracker.completed

        return Response({'status': True, 'rewards': rewards_data})


class ClaimEloRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reward_id = serializer.validated_data['value']

        if reward_id not in request.user.elorewardtracker.completed:
            return Response({'status': False, 'reason': 'have not reached the elo for this reward'})

        elo_reward = get_elo_rewards_list()[reward_id]
        rewards = convert_elo_reward_to_chest_reward(elo_reward, request.user)
        chests.award_chest_rewards(request.user, rewards)

        request.user.elorewardtracker.claimed.append(reward_id)
        request.user.elorewardtracker.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})


def complete_any_elo_rewards(elo: int, tracker: EloRewardTracker):
    for reward in get_elo_rewards_list():
        if reward.elo > elo:
            break
        tracker.completed.append(reward.id)

    tracker.save()
