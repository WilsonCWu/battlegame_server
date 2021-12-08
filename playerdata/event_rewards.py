from datetime import date, datetime, timezone
from functools import lru_cache
from typing import List

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata import chests, serializers, constants
from playerdata.models import EventTimeTracker


def christmas_2021_rewards():
    return [
        chests.ChestReward('chest', constants.ChestType.SILVER.value),  # Day 1
        chests.ChestReward('gems', 888),
        chests.ChestReward('chest', constants.ChestType.GOLD.value),
        chests.ChestReward('gems', 1000),
        chests.ChestReward('chest', constants.ChestType.GOLD.value),
        chests.ChestReward('gems', 1200),
        chests.ChestReward('chest', constants.ChestType.GOLD.value),
        chests.ChestReward('chest', constants.ChestType.MYTHICAL.value)  # Grand Prize (8th)
    ]


# Returns a list[list[ChestReward]]
@lru_cache()
def get_event_rewards_list(event_name: str) -> List[chests.ChestReward]:
    rewards = []

    if event_name == constants.EventType.CHRISTMAS_2021.value:
        rewards = christmas_2021_rewards()

    return rewards


def get_active_event_rewards() -> List[chests.ChestReward]:
    cur_time = datetime.now(timezone.utc)
    event_time = EventTimeTracker.objects.filter(start_time__lte=cur_time, end_time__gt=cur_time).first()
    if event_time is None:
        return []
    else:
        return get_event_rewards_list(event_time.name)


class GetEventRewardListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        last_claimed_reward = request.user.eventrewards.last_claimed_reward
        rewards = get_active_event_rewards()

        return Response({'status': True,
                         'last_claimed': last_claimed_reward,
                         'rewards': chests.ChestRewardSchema(rewards, many=True).data
                         })


class ClaimEventRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        cur_time = datetime.now(timezone.utc)
        if cur_time.day == request.user.eventrewards.last_claimed_time.day:
            return Response({'status': False, 'reason': 'reward for today has been claimed'})

        event_rewards = get_active_event_rewards()
        next_reward_id = request.user.eventrewards.last_claimed_reward + 1

        if event_rewards[next_reward_id].reward_type == "chest":
            rewards = chests.generate_chest_rewards(event_rewards[next_reward_id].value, request.user)
        else:
            rewards = [event_rewards[next_reward_id]]

        request.user.eventrewards.last_claimed_reward = next_reward_id
        request.user.eventrewards.last_claimed_time = cur_time
        request.user.eventrewards.save()

        chests.award_chest_rewards(request.user, rewards)
        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
