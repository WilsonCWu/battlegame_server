from datetime import datetime
from functools import lru_cache
from typing import List

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema
from marshmallow import fields

from playerdata import chests, constants
from playerdata.models import RegalRewards, regal_rewards_refreshdate


class RegalRewardsSchema(Schema):
    is_premium = fields.Bool()
    expiration_date = fields.DateTime()
    points = fields.Int()
    last_completed = fields.Int()
    last_claimed = fields.Int()
    last_claimed_premium = fields.Int()


# Represents a single row in the Regal Rewards list
class RegalRewardRowSchema(Schema):
    id = fields.Int()
    unlock_amount = fields.Int()
    reg_rewards = fields.Nested(chests.ChestRewardSchema, many=True)
    premium_rewards = fields.Nested(chests.ChestRewardSchema, many=True)


class RegalRewardRow:
    def __init__(self, row_id, unlock_amount):
        self.id = row_id
        self.unlock_amount = unlock_amount
        self.reg_rewards = []
        self.premium_rewards = []


# 25 reward intervals
@lru_cache()
def get_regal_rewards_list() -> List[RegalRewardRow]:
    rewards = []
    unlock_amount = 0

    for reward_id in range(0, 25):
        reward_group = RegalRewardRow(reward_id, unlock_amount)

        gems = 200
        rare_shards = 40
        epic_shards = 15

        if reward_id % 5 == 0:
            gems = 800
            rare_shards = 80 * 3
            epic_shards = 80

        reward_group.reg_rewards.append(chests.ChestReward("rare_shards", rare_shards))
        reward_group.premium_rewards.append(chests.ChestReward("epic_shards", epic_shards))
        reward_group.premium_rewards.append(chests.ChestReward("gems", gems))

        rewards.append(reward_group)
        unlock_amount += constants.REGAL_REWARD_INTERVAL

    return rewards


class GetRegalRewardListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        regal_rewards = get_regal_rewards_list()
        rewards_data = RegalRewardRowSchema(regal_rewards, many=True).data

        regal_state = RegalRewardsSchema(request.user.regalrewards)

        return Response({'status': True,
                         'rewards': rewards_data,
                         'regal_state': regal_state.data})


class ClaimRegalRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        regal_rewards = get_regal_rewards_list()

        if not request.user.regalrewards.is_premium:
            request.user.regalrewards.last_claimed += 1
            reward_id = request.user.regalrewards.last_claimed
            rewards = regal_rewards[reward_id].reg_rewards
        elif request.user.regalrewards.last_claimed_premium < request.user.regalrewards.last_claimed:
            request.user.regalrewards.last_claimed_premium += 1
            reward_id = request.user.regalrewards.last_claimed_premium
            rewards = regal_rewards[reward_id].premium_rewards
        else:
            request.user.regalrewards.last_claimed_premium += 1
            request.user.regalrewards.last_claimed += 1
            reward_id = request.user.regalrewards.last_claimed_premium
            rewards = regal_rewards[reward_id].reg_rewards + regal_rewards[reward_id].premium_rewards

        if reward_id > request.user.regalrewards.last_completed:
            return Response({'status': False, 'reason': 'not enough points for this reward'})

        request.user.regalrewards.save()

        chests.award_chest_rewards(request.user, rewards)
        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})


@atomic()
def reset_regal_rewards_cron():
    # reset all passes that are expired
    today = datetime.today()
    refresh_time = datetime(today.year, today.month, today.day, 0)
    new_expiration_date = regal_rewards_refreshdate()
    RegalRewards.objects.filter(expiration_date__lt=refresh_time).update(is_premium=False,
                                                                         expiration_date=new_expiration_date,
                                                                         points=0,
                                                                         last_completed=0,
                                                                         last_claimed=-1,
                                                                         last_claimed_premium=-1)
