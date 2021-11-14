import random
from enum import Enum

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
    JACKPOT = 2


# TODO: tune numbers
NUM_REWARDS_PER_TIER = {
    GrassRewardType.DECENT.value: 4,
    GrassRewardType.GOOD.value: 2,
    GrassRewardType.JACKPOT.value: 1
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
    total_positions = set(range(0, MAP_SIZE))
    reward_map = {}

    for tier, num_rewards in enumerate(NUM_REWARDS_PER_TIER.values()):
        indices = random.sample(total_positions, num_rewards)
        total_positions -= set(indices)

        for index in indices:
            reward_map[index] = tier

    return reward_map


class GetGrassEventView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        event, _ = GrassEvent.objects.get_or_create(user=request.user)
        event_time_tracker = EventTimeTracker.objects.filter(name='grass_event').first()

        if event.floor_reward_map is None:
            event.floor_reward_map = gen_reward_map()
            event.save()

        return Response({'status': True,
                         'grass_event': GrassEventSchema(event).data,
                         'event_time_tracker': event_times.EventTimeTrackerSchema(event_time_tracker).data
                         })


class StartGrassRunView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        event = GrassEvent.objects.get(user=request.user)

        if event.tickets_left < 1:
            return Response({'status': False, 'reason': 'not enough tickets for a run'})

        event.tickets_left -= 1
        event.save()

        return Response({'status': True})


class FinishGrassRunView(APIView):
    permission_classes = (IsAuthenticated,)

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

    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cut_index = serializer.validated_data['value']

        event = GrassEvent.objects.get(user=request.user)

        if event.grass_cuts_left < 1:
            return Response({'status': False, 'reason': 'not enough tokens to cut grass'})

        if cut_index in event.claimed_tiles:
            return Response({'status': False, 'reason': 'already revealed this tile'})

        rewards = []
        reward_type = GrassRewardType.NONE.value
        cut_index_key = str(cut_index)  # JSONs have string keys

        if cut_index_key in event.floor_reward_map:
            reward_type = event.floor_reward_map[cut_index_key]
            rewards = grass_reward(reward_type, event.cur_floor)

            if reward_type == GrassRewardType.JACKPOT.value:
                event.ladder_index = cut_index

        event.claimed_tiles.append(cut_index)
        event.grass_cuts_left -= 1
        event.save()

        return Response({'status': True,
                         'rewards': chests.ChestRewardSchema(rewards, many=True).data,
                         'reward_type': reward_type
                         })


class NextGrassFloorView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ladder_index = serializer.validated_data['value']

        event = GrassEvent.objects.get(user=request.user)

        # Double checking client knows the ladder_index
        if event.ladder_index != ladder_index:
            return Response({'status': False, 'reason': 'invalid ladder_index'})

        event.cur_floor += 1
        event.tokens_bought = 0  # for resetting token costs on the next floor
        event.claimed_tiles = []
        event.ladder_index = -1
        event.floor_reward_map = gen_reward_map()
        event.save()

        return Response({'status': True, 'grass_event': GrassEventSchema(event).data})


# TODO: increase with the number of tokens bought
def grass_cut_cost(tokens_bought):
    return 100


class BuyGrassTokenView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        event = GrassEvent.objects.get(user=request.user)

        gem_cost = grass_cut_cost(event.tokens_bought)
        if request.user.inventory.gems < gem_cost:
            return Response({'status': False, 'reason': 'not enough gems to buy token'})

        event.tokens_bought += 1
        event.grass_cuts_left += 1
        event.save()

        request.user.inventory.gems -= gem_cost
        request.user.inventory.save()

        return Response({'status': True})
