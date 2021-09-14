from typing import List

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema
from marshmallow import fields

from playerdata import chests
from playerdata.models import RegalRewards
from playerdata.serializers import IntSerializer


# Represents a single row in the Regal Rewards list
class RegalRewardRowSchema(Schema):
    id = fields.Int()
    unlock_amount = fields.Int()
    completed = fields.Bool()
    claimed = fields.Bool()
    reg_rewards = fields.Nested(chests.ChestRewardSchema, many=True)
    premium_rewards = fields.Nested(chests.ChestRewardSchema, many=True)


class RegalRewardRow:
    def __init__(self, row_id, unlock_amount):
        self.id = row_id
        self.unlock_amount = unlock_amount
        self.reg_rewards = []
        self.premium_rewards = []


# 25 intervals
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

        for reward in rewards_data:
            reward['claimed'] = reward['id'] <= request.user.regalrewards.last_claimed
            reward['completed'] = reward['id'] <= request.user.regalrewards.last_completed

        return Response({'status': True,
                         'rewards': rewards_data,
                         'is_premium': request.user.regalrewards.is_premium,
                         'expiration_date': request.user.regalrewards.expiration_date})


class ClaimRegalRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reward_id = serializer.validated_data['value']

        if not request.user.regalrewards.is_premium:
            return Response({'status': False, 'reason': 'Regal rewards is not activated'})

        if reward_id > request.user.regalrewards.last_completed:
            return Response({'status': False, 'reason': 'not enough points for this reward'})

        if reward_id != request.user.regalrewards.last_claimed + 1:
            return Response({'status': False, 'reason': 'must claim the next reward in order'})

        regal_rewards = get_regal_rewards_list()[reward_id]
        rewards = regal_rewards.reg_rewards  # get the non-premium rewards
        if request.user.regalrewards.is_premium:
            rewards.extend(regal_rewards.premium_rewards)

        # TODO: uncomment when shards are implemented
        # chests.award_chest_rewards(request.user, rewards)
        request.user.regalrewards.last_claimed = reward_id
        request.user.regalrewards.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
