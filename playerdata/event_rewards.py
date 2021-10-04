from functools import lru_cache
from typing import List
from datetime import date, datetime

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema
from marshmallow import fields

from playerdata import chests, serializers
from playerdata.models import EventRewards


# Returns a list[list[ChestReward]]
@lru_cache()
def get_event_rewards_list() -> List[List[chests.ChestReward]]:
    day_one = []
    day_one.append(chests.ChestReward('char_id', 38))  # Technician
    day_one.append(chests.ChestReward('gems', 500))

    day_two = []
    day_two.append(chests.ChestReward('char_id', 33))  # Demolitionist
    day_two.append(chests.ChestReward('gems', 800))

    day_three = []
    day_three.append(chests.ChestReward('char_id', 37))  # Blob
    day_three.append(chests.ChestReward('gems', 1100))

    day_four = []
    day_four.append(chests.ChestReward('char_id', 35))  # Hunter
    day_four.append(chests.ChestReward('gems', 1400))

    day_five = []
    day_five.append(chests.ChestReward('char_id', 34))  # Spacemage
    day_five.append(chests.ChestReward('gems', 2700))
    day_five.append(chests.ChestReward('profile_pic', 16))  # Profile pic

    return [day_one, day_two, day_three, day_four, day_five]


# Returns an int, number of days passed since event started. First day returns 0
def get_event_rewards_unlocked():
    day0 = date(2021, 10, 13)  # hardcoded to first day of launch event
    delta = (datetime.utcnow().date() - day0).days
    return delta


class GetEventRewardListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        event_rewards = get_event_rewards_list()
        last_claimed_reward = request.user.eventrewards.last_claimed_reward
        last_unlocked_reward = get_event_rewards_unlocked()

        return Response({'status': True,
                         'highest_claimed': last_claimed_reward,
                         'highest_unlocked': last_unlocked_reward})


class ClaimEventRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = serializers.IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reward_id = serializer.validated_data['value']

        # Unlock one at a time, in order
        if reward_id <= request.user.eventrewards.last_claimed_reward:
            return Response({'status': False, 'reason': 'reward has already been claimed'})
        if reward_id > (request.user.eventrewards.last_claimed_reward+1):
            return Response({'status': False, 'reason': 'reward is not unlocked'})

        # One reward unlocked per day after Oct 13
        if reward_id > get_event_rewards_unlocked():
            return Response({'status': False, 'reason': 'reward is not released'})

        event_rewards = get_event_rewards_list()
        rewards = event_rewards[reward_id]
        request.user.eventrewards.last_claimed_reward = reward_id
        request.user.eventrewards.save()

        chests.award_chest_rewards(request.user, rewards)
        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
