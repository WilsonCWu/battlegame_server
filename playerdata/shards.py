import math
import random

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from playerdata import chests, rolls, constants
from playerdata.serializers import SummonShardSerializer

SHARD_SUMMON_COST = 80


def roll_n_chars_of_rarity(wishlist, num_chars: int, rarity: int):
    rewards = []
    for n in range(0, num_chars):
        char_id = rolls.get_wishlist_base_char_from_rarity(wishlist, rarity)
        char_reward = chests.ChestReward(reward_type='char_id', value=char_id)
        rewards.append(char_reward)

    return rewards


def get_shard_attr_from_rarity(rarity: int):
    if rarity == 2:
        shard_type = 'rare_shards'
    elif rarity == 3:
        shard_type = 'epic_shards'
    elif rarity == 4:
        shard_type = 'legendary_shards'
    else:
        raise Exception("invalid summon shard rarity: " + str(rarity))

    return shard_type


def get_afk_shards(num_rolls: int):
    rewards = [0, 0, 0]

    for n in range(0, num_rolls):
        rarity = rolls.weighted_pick_from_buckets(constants.AFK_SHARD_DROP_RATE)
        base_shards = constants.AFK_BASE_SHARD_REWARD[rarity]
        rewards[rarity - 2] += base_shards

    return rewards


# Reward shards if a golden run
def dd_rewards(depth: int):
    # always guarantee epic shard drop
    rarity = 3

    # Reaching the end gives full base_reward amount
    base_shards = constants.DD_BASE_SHARD_REWARD[rarity] / 2
    pivot_amount = math.floor(base_shards + (depth / 20) * base_shards)

    # +/-10% of the pivot amount for some variety
    num_shards = random.randint(math.floor(0.9 * pivot_amount), math.floor(pivot_amount * 1.1))

    shard_type = get_shard_attr_from_rarity(rarity)
    return [chests.ChestReward(reward_type=shard_type, value=num_shards)]


class SummonShardsView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = SummonShardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        num_chars = serializer.validated_data['num_chars']
        rarity = serializer.validated_data['rarity']

        shard_type = get_shard_attr_from_rarity(rarity)
        if num_chars <= 0:
            return Response({'status': False, 'reason': 'invalid num_chars'})

        total_required_shards = num_chars * SHARD_SUMMON_COST
        num_shards = getattr(request.user.inventory, shard_type)

        if num_shards < total_required_shards:
            return Response({'status': False, 'reason': 'not enough shards to summon'})

        num_shards -= total_required_shards
        setattr(request.user.inventory, shard_type, num_shards)

        rewards = roll_n_chars_of_rarity(request.user.wishlist, num_chars, rarity)
        chests.award_chest_rewards(request.user, rewards)

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})
