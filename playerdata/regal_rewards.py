from typing import List

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema
from marshmallow import fields

from playerdata import chests
from playerdata.models import RegalRewards


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


# TODO: Tune reward amounts
# 25 reward intervals
def get_regal_rewards_list() -> List[RegalRewardRow]:
    rewards = []
    unlock_amount = 0

    for reward_id in range(0, 25):
        reward_group = RegalRewardRow(reward_id, unlock_amount)

        gems = 100
        rare_shards = 90
        epic_shards = 30

        if reward_id % 5 == 0:
            gems = 600
            rare_shards = 540
            epic_shards = 180

        reward_group.reg_rewards.append(chests.ChestReward("rare_shards", rare_shards))
        reward_group.premium_rewards.append(chests.ChestReward("epic_shards", epic_shards))
        reward_group.premium_rewards.append(chests.ChestReward("gems", gems))

        rewards.append(reward_group)
        unlock_amount += 800

    return rewards


def complete_regal_rewards(points: int, tracker: RegalRewards):
    for reward_row in get_regal_rewards_list():
        if reward_row.unlock_amount > points:
            break
        tracker.last_completed = max(reward_row.id, tracker.last_completed)

    tracker.save()


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

        if not request.user.regalrewards.is_premium or request.user.regalrewards.last_claimed <= request.user.regalrewards.last_claimed_premium:
            request.user.regalrewards.last_claimed += 1
            reward_id = request.user.regalrewards.last_claimed
            rewards = regal_rewards[reward_id].reg_rewards
        else:
            request.user.regalrewards.last_claimed_premium += 1
            reward_id = request.user.regalrewards.last_claimed_premium
            rewards = regal_rewards[reward_id].premium_rewards

        if reward_id > request.user.regalrewards.last_completed:
            return Response({'status': False, 'reason': 'not enough points for this reward'})

        request.user.regalrewards.save()

        # TODO: uncomment when shards are implemented
        # chests.award_chest_rewards(request.user, rewards)
        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
