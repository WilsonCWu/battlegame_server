from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from playerdata import chests
from playerdata.models import ActivityPoints
from playerdata.serializers import IntSerializer


class ActivityPointsReward:
    def __init__(self, reward_id, unlock_amount, rewards):
        self.id = reward_id
        self.unlock_amount = unlock_amount
        self.rewards = rewards


# TODO: Tune reward numbers
# TODO: can cache too
def get_daily_activitypoints_rewards():
    reward0 = [
        chests.ChestReward("coins", 10000),
        chests.ChestReward("regal_points", 10)
    ]

    reward1 = [
        chests.ChestReward("dust", 150),
        chests.ChestReward("regal_points", 20)
    ]

    reward2 = [
        chests.ChestReward("rare_shards", 5),
        chests.ChestReward("regal_points", 20)
    ]

    reward3 = [
        chests.ChestReward("gems", 50),
        chests.ChestReward("regal_points", 20)
    ]

    reward4 = [
        chests.ChestReward("gems", 100),
        chests.ChestReward("regal_points", 50)
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
        for reward in get_daily_activitypoints_rewards():
            if reward.unlock_amount > points:
                break
            activity_points.daily_last_completed = max(reward.id, activity_points.daily_last_completed)

        activity_points.save()


class ClaimActivityPointsView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        activity_type = serializer.validated_data['value']  # 0 is daily, 1 is weekly

        # if max reached return false

        # if none claimable return false

        if activity_type == 0:
            if request.user.activitypoints.daily_last_claimed >= request.user.activitypoints.daily_last_completed:
                return Response({'status': False, 'reason': 'have not completed this reward yet'})

            reward_id = request.user.activitypoints.daily_last_claimed + 1
            rewards = get_daily_activitypoints_rewards()[reward_id].rewards

        else:
            pass

        # TODO: uncomment when shards are implemented
        # chests.award_chest_rewards(request.user, rewards)
        request.user.activitypoints.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
