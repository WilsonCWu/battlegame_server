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
from playerdata.serializers import IntSerializer

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
    coin_hours, dust_hours = 0, 0
    rare_shards, epic_shards, leg_shards = 0, 0, 0

    if reward_type == constants.GrassRewardType.DECENT.value:
        coin_hours = 1 + (floor - 1) // 2
    elif reward_type == constants.GrassRewardType.GOOD.value:
        coin_hours = 3 + (floor - 1) // 2
        rare_shards = 10 + (floor - 1) * 2.5
    elif reward_type == constants.GrassRewardType.GREAT.value:
        epic_shards = int(10 + (floor - 1) * 2.5)
        dust_hours = 2 + (floor - 1) // 2
    elif reward_type == constants.GrassRewardType.JACKPOT.value:
        if floor == 15:
            dust_hours = 40
            epic_shards = 80 * 4
            leg_shards = 80 * 2
        else:
            dust_hours = 5 + (floor - 1) * 1
            epic_shards = 45 + (floor - 1) * 4
            leg_shards = 5 + (floor - 1) * 3
        if floor == 1:
            rewards.append(chests.ChestReward('pet_id', 6))
    else:
        raise Exception("invalid grass_event reward_type")

    if coin_hours > 0:
        rewards.append(chests.ChestReward(constants.RewardType.COINS_FAST_REWARDS.value, coin_hours))
    if dust_hours > 0:
        rewards.append(chests.ChestReward(constants.RewardType.DUST_FAST_REWARDS.value, dust_hours))
    if rare_shards > 0:
        rewards.append(chests.ChestReward(constants.RewardType.RARE_SHARDS.value, rare_shards))
    if epic_shards > 0:
        rewards.append(chests.ChestReward(constants.RewardType.EPIC_SHARDS.value, epic_shards))
    if leg_shards > 0:
        rewards.append(chests.ChestReward(constants.RewardType.LEGENDARY_SHARDS.value, leg_shards))

    return rewards


def get_all_rewards_json():
    all_rewards = []
    for floor in range(1, 16):
        floor_rewards = []
        for reward_type in constants.GRASS_REWARDS_PER_TIER:
            floor_rewards.append({'rewards': chests.ChestRewardSchema(grass_reward(reward_type, floor), many=True).data})
        all_rewards.append({'floors': floor_rewards})
    return all_rewards


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
                         'next_token_reset': next_token_reset_time(),
                         'rewards_list': get_all_rewards_json()
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
        # hardcode first pick on floor 1 to be a Great reward type
        if event.cur_floor == 1 and len(event.claimed_tiles) == 0:
            reward_type = constants.GrassRewardType.GREAT.value

        rewards = grass_reward(reward_type, event.cur_floor)
        chests.award_chest_rewards(request.user, rewards)

        if reward_type == constants.GrassRewardType.JACKPOT.value:
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
    base_amount = 50

    if cur_floor == 1:
        extra_amount = 0
    elif cur_floor < 5:
        extra_amount = 40 + (cur_floor - 1) * 10
    elif cur_floor < 10:
        extra_amount = 90 + (cur_floor - 1) * 15
    else:
        extra_amount = 150 + (cur_floor - 1) * 20

    return int(base_amount + extra_amount)


# Test functions to print out cost / reward values

def print_floor_cost(floor):
    for n in range(0, 25):
        print(grass_cut_cost(n, floor))


def print_all_rewards():
    grand_total_value = 0
    total_cost = 0
    expected_cost_f2p = 0
    expected_value_f2p = 0
    for floor in range(1, 16):
        print(f"Floor {floor}")
        print(f"Total cost: {total_cost_per_floor(floor)} Average: {total_cost_per_floor(floor)/25}")
        print(f"Total value: {total_value_per_floor(floor)}")
        for reward_type in constants.GRASS_REWARDS_PER_TIER:
            print(grass_reward(reward_type, floor))
        print("")
        grand_total_value += total_value_per_floor(floor)
        total_cost += total_cost_per_floor(floor)

        if floor <= 7:
            expected_cost_f2p += total_cost_per_floor(floor) / 2
            expected_value_f2p += total_value_per_floor(floor)

    print(f"Final value: {grand_total_value}")
    print(f"Final cost: {total_cost}")
    print(f"Expected cost f2p: {expected_cost_f2p}")
    print(f"Expected value f2p: {expected_value_f2p}")


def total_value_per_floor(floor):
    total = 0
    for reward_type in constants.GRASS_REWARDS_PER_TIER:
        rewards = grass_reward(reward_type, floor)
        total += sum([reward.gem_value() for reward in rewards])
    return total


def total_cost_per_floor(floor):
    total = 0
    for n in range(0, 25):
        total += grass_cut_cost(n, floor)
    return total
