from datetime import datetime, timezone, timedelta
import math

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from playerdata import server, shards
from playerdata.formulas import afk_coins_per_min, afk_exp_per_min, afk_dust_per_min, vip_exp_to_level
from playerdata.models import DungeonProgress, AFKReward, default_afk_shard_list
from playerdata.serializers import FastRewardsSerializer

PVP_RUNE_REWARD = 3600  # 1 hr worth of afk
RUNES_FULL = -1


# Return seconds since last datetime capped at the afk time maximum
def afk_secs_since_last_datetime(last_datetime, vip_level: int):
    now_time = datetime.now(timezone.utc)
    elapsed = now_time - last_datetime
    elapsed_secs = elapsed.total_seconds()

    max_hours = 12 + vip_afk_extra_hours(vip_level)
    return min(max_hours * 60.0 * 60.0, elapsed_secs)


def get_accumulated_runes_limit(vip_level: int):
    return (24 + vip_afk_extra_hours(vip_level)) * 60 * 60


def afk_secs_elapsed_between(datetime1, datetime2, vip_level: int):
    elapsed = datetime1 - datetime2
    elapsed_secs = elapsed.total_seconds()

    max_hours = 12 + vip_afk_extra_hours(vip_level)
    return min(max_hours * 60 * 60, elapsed_secs)


# Calculate the number of runes consumed given the time it had to run
def evaluate_afk_reward_ticks(afk_rewards: AFKReward, vip_level: int, added_runes=0):
    max_hours = 12 + vip_afk_extra_hours(vip_level)
    max_runes_in_bank = (24 + vip_afk_extra_hours(vip_level)) * 60 * 60

    # No runes ticked if past the afk deadline
    afk_deadline = afk_rewards.last_collected_time + timedelta(hours=max_hours)
    cur_time = datetime.now(timezone.utc)
    cur_eval_time = min(cur_time, afk_deadline)

    elapsed_afk_secs = max(afk_secs_elapsed_between(cur_eval_time, afk_rewards.last_eval_time, vip_level), 0)

    # runes_completed needs to be capped by:
    # elapsed secs and the runes left
    runes_completed = min(elapsed_afk_secs, afk_rewards.runes_left)

    # update values
    afk_rewards.last_eval_time = cur_time
    afk_rewards.runes_left = min(max_runes_in_bank, afk_rewards.runes_left + added_runes - runes_completed)
    # counting elapsed_afk_secs + any runes that ticked during that time
    afk_rewards.reward_ticks += runes_completed + elapsed_afk_secs

    afk_rewards.save()
    return afk_rewards


# Number of ticks/secs defined for a shard drop interval
# Example: 60 secs x 15 minutes per shard drop
def PER_SHARD_INTERVAL():
    # Doubling for standard afk time + rune ticks
    return 60 * 15 * 2


class GetAFKRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dungeon_progress = DungeonProgress.objects.get(user=request.user)

        vip_level = vip_exp_to_level(request.user.userinfo.vip_exp)

        coins_per_min = afk_coins_per_min(dungeon_progress.campaign_stage)
        dust_per_min = afk_dust_per_min(dungeon_progress.campaign_stage)
        # exp_per_min = afk_exp_per_min(dungeon_progress.stage_id)

        coins_per_second = coins_per_min / 60
        dust_per_second = dust_per_min / 60

        afk_rewards = evaluate_afk_reward_ticks(request.user.afkreward, vip_level)

        afk_rewards.unclaimed_gold += afk_rewards.reward_ticks * coins_per_second * afk_rewards_multiplier_vip(vip_level)
        afk_rewards.unclaimed_dust += afk_rewards.reward_ticks * dust_per_second * afk_rewards_multiplier_vip(vip_level)

        # roll shards every PER_SHARD_INTERVAL()
        shard_intervals = (afk_rewards.reward_ticks / PER_SHARD_INTERVAL()) + afk_rewards.leftover_shard_interval
        shard_intervals_floored = math.floor(shard_intervals)
        afk_rewards.leftover_shard_interval = shard_intervals - shard_intervals_floored

        shards_dropped = shards.get_afk_shards(shard_intervals_floored)

        for i, shard_amount in enumerate(shards_dropped):
            afk_rewards.unclaimed_shards[i] += shard_amount

        # Keep track of the amount of rewards (in terms of runes) that are unclaimed so we can cap it
        afk_rewards.reward_ticks = 0
        afk_rewards.save()

        return Response({'status': True,
                         'coins_per_min': coins_per_min,
                         'dust_per_min': dust_per_min,
                         # 'exp_per_min': exp_per_min,
                         'last_collected_time': afk_rewards.last_collected_time,
                         # 'exp': exp
                         'unclaimed_gold': afk_rewards.unclaimed_gold,
                         'unclaimed_dust': afk_rewards.unclaimed_dust,
                         'unclaimed_shards': afk_rewards.unclaimed_shards,
                         'runes_left': afk_rewards.runes_left
                         })


class CollectAFKRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        coins_floored = math.floor(request.user.afkreward.unclaimed_gold)
        dust_floored = math.floor(request.user.afkreward.unclaimed_dust)

        inventory = request.user.inventory
        inventory.coins += coins_floored
        inventory.dust += dust_floored
        inventory.rare_shards += request.user.afkreward.unclaimed_shards[0]
        inventory.epic_shards += request.user.afkreward.unclaimed_shards[1]
        inventory.legendary_shards += request.user.afkreward.unclaimed_shards[2]

        request.user.afkreward.last_collected_time = datetime.now(timezone.utc)
        request.user.afkreward.unclaimed_gold -= coins_floored
        request.user.afkreward.unclaimed_dust -= dust_floored
        request.user.afkreward.unclaimed_shards = default_afk_shard_list()
        request.user.afkreward.save()

        # request.user.userinfo.player_exp += exp
        # request.user.userinfo.save()

        inventory.save()

        return Response({'status': True})


# Design to be used for either redeeming either both dust or coin fast rewards
class CollectFastRewardsView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = FastRewardsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        dust_hours = serializer.validated_data['dust_hours']
        coin_hours = serializer.validated_data['coin_hours']

        if dust_hours > request.user.inventory.dust_fast_reward_hours or coin_hours > request.user.inventory.coins_fast_reward_hours:
            return Response({'status': False, 'reason': 'not enough hours available to redeem'})

        dungeon_progress = DungeonProgress.objects.get(user=request.user)

        # Just like in AFK Arena, VIP bonus doesn't apply here
        dust = dust_hours * 60 * afk_dust_per_min(dungeon_progress.campaign_stage)
        coins = coin_hours * 60 * afk_coins_per_min(dungeon_progress.campaign_stage)

        request.user.inventory.dust += dust
        request.user.inventory.coins += coins
        request.user.inventory.save()

        return Response({'status': True, 'coins': coins, 'dust': dust})


def afk_rewards_multiplier_vip(level: int):
    # TODO: flip to on whenever we launch VIP
    if not server.is_server_version_higher("2.0.0"):
        return 1

    if level == 1:
        return 1.05
    elif level == 2:
        return 1.1
    elif level == 2:
        return 1.15
    elif level == 3:
        return 1.2
    elif level == 4:
        return 1.25
    elif level == 5:
        return 1.3
    elif level == 6:
        return 1.5
    elif level == 7:
        return 1.55
    elif level == 8:
        return 1.6
    elif level == 9:
        return 1.9
    elif level == 10:
        return 2
    elif level == 11:
        return 2.1
    elif level == 12:
        return 2.5
    elif level == 13:
        return 2.6
    elif level == 14:
        return 3
    elif level == 15:
        return 3.3
    elif level == 16:
        return 3.6
    elif level >= 17:
        return 4
    else:
        return 1


def vip_afk_extra_hours(level: int):
    # TODO: flip to on whenever we launch VIP
    if not server.is_server_version_higher("2.0.0"):
        return 0

    if level == 3:
        return 2
    elif level == 4:
        return 4
    elif level == 5:
        return 6
    elif level == 6:
        return 12
    elif level == 7:
        return 24
    elif level == 8:
        return 48
    elif level == 9:
        return 72
    elif level == 10:
        return 120
    elif level == 11:
        return 168
    elif level == 12:
        return 216
    elif level == 13:
        return 336
    elif level == 14:
        return 480
    elif level >= 15:
        return 720
    else:
        return 0
