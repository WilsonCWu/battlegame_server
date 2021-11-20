import random
from typing import List
from datetime import datetime, timedelta

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from . import chests, constants
from playerdata import event_times
from playerdata.models import GrassEvent, EventTimeTracker, default_grass_rewards_left
from playerdata.serializers import BooleanSerializer, IntSerializer

MAP_SIZE = 25


class GrassEventSchema(Schema):
    cur_floor = fields.Int()
    ladder_index = fields.Int()
    unclaimed_tokens = fields.Int()
    grass_cuts_left = fields.Int()
    tokens_bought = fields.Int()
    claimed_tiles = fields.List(fields.Int())
    rewards_left = fields.List(fields.Int())


""" Reward amounts visualized
        Floor 1	Floor 2	Floor 3	Floor 4	Floor 5	Floor 6	Floor 7	Floor 8
DECENT	25      50      75      100     125     150     175     200
GOOD	300     350     400     450     500     550     600     650
GREAT	1,500	1,800	2,100	2,400	2,700	3,000	3,300	3,600
JACKPOT	5,000	6,000	7,000	8,000	9,000	10,000	12,000	25,000
"""


def grass_reward(reward_type, floor):
    rewards = []
    gems = 0
    dust = 0
    leg_shards = 0

    if reward_type == constants.GrassRewardType.DECENT.value:
        gems = 25 + (floor - 1) * 25
    elif reward_type == constants.GrassRewardType.GOOD.value:
        gems = 300 + (floor - 1) * 50
    elif reward_type == constants.GrassRewardType.GREAT.value:
        gems = 1500 + (floor - 1) * 300
    elif reward_type == constants.GrassRewardType.JACKPOT.value:
        if floor == 8:
            gems = 25000
            dust = 10000
            leg_shards = 80 * 5
        else:
            gems = 5000 + (floor - 1) * 1000
            dust = 1000 + (floor - 1) * 500
            leg_shards = 80

            # Award the Turkey on Floor 1 jackpot
            if floor == 1:
                rewards.append(chests.ChestReward('pet_id', 9))
    elif reward_type == constants.GrassRewardType.LADDER.value:
        pass
    else:
        raise Exception("invalid grass_event reward_type")

    if gems > 0:
        rewards.append(chests.ChestReward('gems', gems))
    if dust > 0:
        rewards.append(chests.ChestReward('dust', dust))
    if leg_shards > 0:
        rewards.append(chests.ChestReward('legendary_shards', leg_shards))

    return rewards


# picks a random reward_type out of the rewards left
def pick_rand_reward_left(rewards_left: List[int]):
    pick_list = random.choices(population=list(constants.GRASS_REWARDS_PER_TIER.keys()),
                               weights=rewards_left,
                               k=1
                               )

    return pick_list[0]  # random.choices returns a list


# Returns the next odd day datetime
def next_token_reset_time():
    today = datetime.today()
    if today.day % 2 == 1:
        return datetime(today.year, today.month, today.day, 0) + timedelta(days=2)
    else:
        return datetime(today.year, today.month, today.day, 0) + timedelta(days=1)


class GetGrassEventView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def get(self, request):
        event, is_event_created = GrassEvent.objects.get_or_create(user=request.user)
        event_time_tracker = EventTimeTracker.objects.filter(name=constants.EventType.GRASS.value).first()

        return Response({'status': True,
                         'grass_event': GrassEventSchema(event).data,
                         'event_time_tracker': event_times.EventTimeTrackerSchema(event_time_tracker).data,
                         'next_token_reset': next_token_reset_time()
                         })


class FinishGrassRunView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        won_tokens = serializer.validated_data['value']

        event = GrassEvent.objects.get(user=request.user)

        claimed_tokens = min(won_tokens, event.unclaimed_tokens)
        event.grass_cuts_left += claimed_tokens
        event.unclaimed_tokens -= claimed_tokens
        event.save()

        return Response({'status': True, 'tokens_left': event.grass_cuts_left})


class CutGrassView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cut_index = serializer.validated_data['value']

        event = GrassEvent.objects.get(user=request.user)

        if cut_index in event.claimed_tiles:
            return Response({'status': False, 'reason': 'already revealed this tile'})

        # use gems to cut grass if no more grass_cuts_left
        if event.grass_cuts_left < 1:
            gem_cost = grass_cut_cost(event.tokens_bought, event.cur_floor)
            if request.user.inventory.gems < gem_cost:
                return Response({'status': False, 'reason': 'not enough gems to buy token'})

            event.tokens_bought += 1

            request.user.inventory.gems -= gem_cost
            request.user.inventory.save()
        else:
            event.grass_cuts_left -= 1

        reward_type = pick_rand_reward_left(event.rewards_left)
        rewards = grass_reward(reward_type, event.cur_floor)

        if reward_type == constants.GrassRewardType.LADDER.value:
            event.ladder_index = cut_index

        event.rewards_left[reward_type] -= 1
        event.claimed_tiles.append(cut_index)
        event.save()

        return Response({'status': True,
                         'rewards': chests.ChestRewardSchema(rewards, many=True).data,
                         'reward_type': reward_type
                         })


# this is called when player decides to go through the ladder
# we don't immediately go to next floor to let the player
# collect more rewards if they want to stay
class NextGrassFloorView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        event = GrassEvent.objects.get(user=request.user)

        # Check that the ladder was found
        if event.ladder_index == -1:
            return Response({'status': False, 'reason': 'invalid ladder_index'})

        # reset any state from the previous floor
        event.cur_floor += 1
        event.tokens_bought = 0  # for resetting token costs on the next floor
        event.claimed_tiles = []
        event.ladder_index = -1
        event.rewards_left = default_grass_rewards_left()
        event.save()

        return Response({'status': True, 'grass_event': GrassEventSchema(event).data})


def grass_cut_cost(tokens_bought, cur_floor):
    base_amount = 25 + (cur_floor - 1) * 25

    if tokens_bought <= 1:
        extra_amount = tokens_bought * 25
    elif tokens_bought <= 3:
        extra_amount = tokens_bought * 50
    elif tokens_bought <= 7:
        extra_amount = tokens_bought * 75
    elif tokens_bought <= 11:
        extra_amount = tokens_bought * 85
    else:
        extra_amount = tokens_bought * 90

    return base_amount + extra_amount


# Test functions to print out cost / reward values

def print_floor_cost(floor):
    for n in range(0, 25):
        print(grass_cut_cost(n, floor))


def print_all_rewards():
    for floor in range(1, 9):
        print(f"Floor {floor}")
        for reward_type in constants.GRASS_REWARDS_PER_TIER:
            print(grass_reward(reward_type, floor))
        print("")
