from django.db import transaction
from datetime import datetime, timedelta, timezone

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from . import chests
from .models import BaseCode, ClaimedCode


class ClaimConquestEventRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        # Using the Redemption Code model to do one-time reward claiming for the conquest event
        event_code = "conquest_event_reward_code"
        if ClaimedCode.objects.filter(user=request.user, code__code=event_code).exists():
            return Response({'status': False, 'reason': 'reward has already been claimed'})

        base_code = BaseCode.objects.filter(code=event_code).first()
        if base_code is None:
            curr_time = datetime.now(timezone.utc)
            end_time = curr_time + + timedelta(days=365)
            base_code = BaseCode.objects.create(code=event_code, start_time=curr_time, end_time=end_time)
        ClaimedCode.objects.create(user=request.user, code=base_code)

        rewards = []
        rewards.append(chests.ChestReward('gems', 2700*3))
        rewards.append(chests.ChestReward('profile_pic', 16))

        chests.award_chest_rewards(request.user, rewards)
        reward_schema = chests.ChestRewardSchema(rewards, many=True)

        return Response({'status': True, 'rewards': reward_schema.data})
