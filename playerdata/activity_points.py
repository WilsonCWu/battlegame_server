from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_marshmallow import Schema
from marshmallow import fields

from playerdata import chests, constants
from playerdata.models import ActivityPoints
from playerdata.serializers import IntSerializer


class ActivityPointsSchema(Schema):
    daily_last_completed = fields.Int()
    daily_last_claimed = fields.Int()
    weekly_last_completed = fields.Int()
    weekly_last_claimed = fields.Int()
    daily_points = fields.Int()
    weekly_points = fields.Int()


class ActivityPointsReward:
    def __init__(self, reward_id, unlock_amount, rewards):
        self.id = reward_id
        self.unlock_amount = unlock_amount
        self.rewards = rewards


# TODO: Tune reward numbers
# TODO: can cache too
def get_daily_activitypoints_rewards():
    reward0 = [
        chests.ChestReward(constants.RewardType.GEMS.value, 20),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 40)
    ]

    reward1 = [
        chests.ChestReward(constants.RewardType.COINS_FAST_REWARDS.value, 2),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 50)
    ]

    reward2 = [
        chests.ChestReward(constants.RewardType.RARE_SHARDS.value, 10),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 60)
    ]

    reward3 = [
        chests.ChestReward(constants.RewardType.GEMS.value, 60),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 80)
    ]

    reward4 = [
        chests.ChestReward(constants.RewardType.GEMS.value, 100),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 130)
    ]

    rewards = [reward0, reward1, reward2, reward3, reward4]
    activity_rewards = []

    for reward_id, reward in enumerate(rewards):
        unlock_amount = 20 + (reward_id * 20)
        activity_rewards.append(ActivityPointsReward(reward_id, unlock_amount, reward))

    return activity_rewards


# TODO: Tune reward numbers
# TODO: can cache too
def get_weekly_activitypoints_rewards():
    reward0 = [
        chests.ChestReward(constants.RewardType.GEMS.value, 30),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 180)
    ]

    reward1 = [
        chests.ChestReward(constants.RewardType.GEMS.value, 70),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 260)
    ]

    reward2 = [
        chests.ChestReward(constants.RewardType.COINS_FAST_REWARDS.value, 8),
        chests.ChestReward(constants.RewardType.GEMS.value, 100),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 380)
    ]

    reward3 = [
        chests.ChestReward(constants.RewardType.DUST_FAST_REWARDS.value, 2),
        chests.ChestReward(constants.RewardType.GEMS.value, 300),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 400)
    ]

    reward4 = [
        chests.ChestReward(constants.RewardType.COINS_FAST_REWARDS.value, 8),
        chests.ChestReward(constants.RewardType.GEMS.value, 400),
        chests.ChestReward(constants.RewardType.REGAL_POINTS.value, 500)
    ]

    rewards = [reward0, reward1, reward2, reward3, reward4]
    activity_rewards = []

    for reward_id, reward in enumerate(rewards):
        unlock_amount = 20 + (reward_id * 20)
        activity_rewards.append(ActivityPointsReward(reward_id, unlock_amount, reward))

    return activity_rewards


class ActivityPointsUpdater:

    @staticmethod
    @atomic
    def try_complete_daily_activity_points(activity_points: ActivityPoints, points: int):
        activity_points.daily_points += points
        for reward in get_daily_activitypoints_rewards():
            if reward.unlock_amount > activity_points.daily_points:
                break
            activity_points.daily_last_completed = max(reward.id, activity_points.daily_last_completed)

        activity_points.save()

    @staticmethod
    @atomic
    def try_complete_weekly_activity_points(activity_points: ActivityPoints, points: int):
        activity_points.weekly_points += points
        for reward in get_weekly_activitypoints_rewards():
            if reward.unlock_amount > activity_points.weekly_points:
                break
            activity_points.weekly_last_completed = max(reward.id, activity_points.weekly_last_completed)

        activity_points.save()


class ClaimActivityPointsView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity_type = serializer.validated_data['value']  # 0 is daily, 1 is weekly

        if activity_type == 0:
            last_claimed = request.user.activitypoints.daily_last_claimed
            last_completed = request.user.activitypoints.daily_last_completed
        else:
            last_claimed = request.user.activitypoints.weekly_last_claimed
            last_completed = request.user.activitypoints.weekly_last_completed

        if last_claimed >= last_completed:
            return Response({'status': False, 'reason': 'have not completed this reward yet'})

        if activity_type == 0:
            request.user.activitypoints.daily_last_claimed += 1
            rewards = get_daily_activitypoints_rewards()[request.user.activitypoints.daily_last_claimed].rewards
        else:
            request.user.activitypoints.weekly_last_claimed += 1
            rewards = get_weekly_activitypoints_rewards()[request.user.activitypoints.weekly_last_claimed].rewards

        chests.award_chest_rewards(request.user, rewards)
        request.user.activitypoints.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})


@atomic
def reset_daily_activity_points():
    ActivityPoints.objects.update(daily_last_completed=-1, daily_last_claimed=-1, daily_points=0)


@atomic
def reset_weekly_activity_points():
    ActivityPoints.objects.update(weekly_last_completed=-1, weekly_last_claimed=-1, weekly_points=0)
