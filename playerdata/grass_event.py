import random
from enum import Enum

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from . import chests
from playerdata import event_times
from playerdata.models import GrassEvent, EventTimeTracker
from playerdata.serializers import BooleanSerializer, IntSerializer


class GrassRewardType(Enum):
    NONE = -1
    DECENT = 0
    GOOD = 1
    GREAT = 2
    LADDER = 3
    JACKPOT = 4


# TODO: tune numbers
NUM_REWARDS_PER_TIER = {
    GrassRewardType.DECENT.value: 15,
    GrassRewardType.GOOD.value: 5,
    GrassRewardType.GREAT.value: 3,
    GrassRewardType.JACKPOT.value: 1,
    GrassRewardType.LADDER.value: 1,
}
MAP_SIZE = 25


class GrassEventSchema(Schema):
    cur_floor = fields.Int()
    ladder_index = fields.Int()
    tickets_left = fields.Int()
    grass_cuts_left = fields.Int()
    tokens_bought = fields.Int()
    claimed_tiles = fields.List(fields.Int())


# TODO: some increase based on the floor?
def grass_reward(reward_type, floor):
    return []


# returns a randomly generated map of {<int>: <grass_reward_type>}
# if an index isn't in the map, there is no reward there
def gen_reward_map():
    all_tiles = set(range(0, MAP_SIZE))
    reward_map = {}

    for tier, num_rewards in enumerate(NUM_REWARDS_PER_TIER.values()):
        picked_tiles = random.sample(all_tiles, num_rewards)
        all_tiles -= set(picked_tiles)

        for index in picked_tiles:
            reward_map[index] = tier

    return reward_map


class GetGrassEventView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def get(self, request):
        event, is_event_created = GrassEvent.objects.get_or_create(user=request.user)
        event_time_tracker = EventTimeTracker.objects.filter(name='grass_event').first()

        if is_event_created:
            event.floor_reward_map = gen_reward_map()
            event.save()

        return Response({'status': True,
                         'grass_event': GrassEventSchema(event).data,
                         'event_time_tracker': event_times.EventTimeTrackerSchema(event_time_tracker).data
                         })


class StartGrassRunView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        event = GrassEvent.objects.get(user=request.user)

        if event.tickets_left < 1:
            return Response({'status': False, 'reason': 'not enough tickets for a run'})

        event.tickets_left -= 1
        event.save()

        return Response({'status': True})


class FinishGrassRunView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = BooleanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_win = serializer.validated_data['value']

        event = GrassEvent.objects.get(user=request.user)

        if is_win:
            event.grass_cuts_left += 1  # TODO: figure out if we want more than 1 per run?
            event.save()

        return Response({'status': True})


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

        rewards = []
        reward_type = GrassRewardType.NONE.value
        cut_index_key = str(cut_index)  # JSONs have string keys

        if cut_index_key in event.floor_reward_map:
            reward_type = event.floor_reward_map[cut_index_key]
            rewards = grass_reward(reward_type, event.cur_floor)

            if reward_type == GrassRewardType.LADDER.value:
                event.ladder_index = cut_index

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
        event.floor_reward_map = gen_reward_map()
        event.save()

        return Response({'status': True, 'grass_event': GrassEventSchema(event).data})


# TODO: increase with the number of tokens bought
def grass_cut_cost(tokens_bought, cur_floor):
    return 100
