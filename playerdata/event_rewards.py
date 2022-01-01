from datetime import datetime, timezone
from functools import lru_cache
from typing import List

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from mainsocket import notifications
from playerdata import chests, constants
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


def get_active_login_event_rewards() -> List[chests.ChestReward]:
    event_time = get_active_login_event()
    if event_time is None:
        return []
    else:
        return get_event_rewards_list(event_time.name)


def get_active_login_event():
    cur_time = datetime.now(timezone.utc)
    return EventTimeTracker.objects.filter(start_time__lte=cur_time, end_time__gt=cur_time, is_login_event=True).first()


def decrement_active_login_event_notifs(user_id, count):
    event_time = get_active_login_event()
    if event_time is None:
        return

    if event_time.name == constants.EventType.CHRISTMAS_2021.value:
        notifications.send_badge_notifs_increment(user_id, notifications.BadgeNotif(constants.NotificationType.CHRISTMAS_2021.value, count))


class GetEventRewardListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        last_claimed_reward = request.user.eventrewards.last_claimed_reward
        rewards = get_active_login_event_rewards()
        cur_time = datetime.now(timezone.utc)
        is_next_claimable = cur_time.toordinal() > request.user.eventrewards.last_claimed_time.toordinal() and last_claimed_reward < len(rewards)

        return Response({'status': True,
                         'last_claimed': last_claimed_reward,
                         'is_next_claimable': is_next_claimable,
                         'rewards': chests.ChestRewardSchema(rewards, many=True).data
                         })


class ClaimEventRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        cur_time = datetime.now(timezone.utc)

        event_rewards = get_active_login_event_rewards()
        next_reward_id = request.user.eventrewards.last_claimed_reward + 1

        # Completing the 7th day also unlocks the jackpot, allow a double claim
        is_not_jackpot = next_reward_id != len(event_rewards) - 1
        if cur_time.toordinal() == request.user.eventrewards.last_claimed_time.toordinal() and is_not_jackpot:
            return Response({'status': False, 'reason': 'reward for today has been claimed'})

        if next_reward_id >= len(event_rewards):
            return Response({'status': False, 'reason': 'rewards all claimed'})

        next_reward = event_rewards[next_reward_id]

        if next_reward.reward_type == "chest":
            rewards = chests.generate_chest_rewards(next_reward.value, request.user)
        else:
            rewards = [next_reward]

        request.user.eventrewards.last_claimed_reward = next_reward_id
        request.user.eventrewards.last_claimed_time = cur_time
        request.user.eventrewards.save()

        decrement_active_login_event_notifs(request.user.id, -1)

        chests.award_chest_rewards(request.user, rewards)
        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
