from datetime import datetime, timezone
import math

from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from playerdata import server, shards
from playerdata.formulas import afk_coins_per_min, afk_exp_per_min, afk_dust_per_min, vip_exp_to_level
from playerdata.models import DungeonProgress, AFKReward, default_afk_shard_list

PVP_RUNE_REWARD = 3600  # 1 hr worth of afk
SHARDS_PER_INTERVAL = 60 * 15


# Return seconds since last datetime capped at the afk time maximum
def afk_secs_since_last_datetime(last_datetime, vip_level: int):
    now_time = datetime.now(timezone.utc)
    elapsed = now_time - last_datetime
    elapsed_secs = elapsed.total_seconds()

    max_hours = 12 + vip_afk_extra_hours(vip_level)
    return min(max_hours * 60.0 * 60.0, elapsed_secs)


# Calculate the number of runes consumed given the time it had to run
def evaluate_afk(afk_rewards: AFKReward, vip_level: int, added_runes=0):
    max_hours = 12 + vip_afk_extra_hours(vip_level)
    max_runes = max_hours * 60 * 60

    # the max number of runes that can still be converted to rewards on top of what's already converted
    runes_conversion_cap = max_runes - afk_rewards.unclaimed_converted_runes

    # stop consuming runes if capped out on both converted runes or to-be-converted runes
    if afk_rewards.unclaimed_converted_runes >= max_runes or afk_rewards.runes_to_be_converted >= runes_conversion_cap:
        afk_rewards.runes_left = min(max_runes, afk_rewards.runes_left + added_runes)
        return afk_rewards

    # runes_complete needs to be capped by 3 things:
    # elapsed secs, amount of runes that can still be converted, and the runes available
    elapsed_secs = int(afk_secs_since_last_datetime(afk_rewards.last_eval_time, vip_level))
    runes_complete = min(elapsed_secs, runes_conversion_cap, afk_rewards.runes_left)

    # update values
    afk_rewards.last_eval_time = datetime.now(timezone.utc)
    afk_rewards.runes_left = min(max_runes, afk_rewards.runes_left + added_runes - runes_complete)

    # capped at the max runes available to be converted
    # adding runes_complete is guaranteed to be <= runes_conversion_cap
    afk_rewards.runes_to_be_converted += runes_complete

    afk_rewards.save()
    return afk_rewards


class GetAFKRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dungeon_progress = DungeonProgress.objects.get(user=request.user)
        last_collected_time = request.user.inventory.last_collected_rewards

        vip_level = vip_exp_to_level(request.user.userinfo.vip_exp)

        coins_per_min = afk_coins_per_min(dungeon_progress.campaign_stage)
        dust_per_min = afk_dust_per_min(dungeon_progress.campaign_stage)
        # exp_per_min = afk_exp_per_min(dungeon_progress.stage_id)

        time = afk_secs_since_last_datetime(last_collected_time, vip_level)
        coins_per_second = coins_per_min / 60
        dust_per_second = dust_per_min / 60

        coins = math.floor(time * coins_per_second * afk_rewards_multiplier_vip(vip_level))
        dust = math.floor(time * dust_per_second * afk_rewards_multiplier_vip(vip_level))
        # exp = time * exp_per_min

        if server.is_server_version_higher('0.5.0'):
            afk_rewards = evaluate_afk(request.user.afkreward, vip_level)

            afk_rewards.unclaimed_gold += math.floor(afk_rewards.runes_to_be_converted * coins_per_second * afk_rewards_multiplier_vip(vip_level))
            afk_rewards.unclaimed_dust += math.floor(afk_rewards.runes_to_be_converted * dust_per_second * afk_rewards_multiplier_vip(vip_level))

            # roll shards once every 15 minutes
            shard_runes_consumed = afk_rewards.runes_to_be_converted + afk_rewards.leftover_shards
            shard_rolls = math.floor(shard_runes_consumed / SHARDS_PER_INTERVAL)

            afk_rewards.leftover_shards = max(0, shard_runes_consumed - (shard_rolls * SHARDS_PER_INTERVAL))
            shards_dropped = shards.get_afk_shards(shard_rolls)

            for i, shard_amount in enumerate(shards_dropped):
                afk_rewards.unclaimed_shards[i] += shard_amount

            # Keep track of the amount of rewards (in terms of runes) that are unclaimed so we can cap it
            afk_rewards.unclaimed_converted_runes += afk_rewards.runes_to_be_converted
            afk_rewards.runes_to_be_converted = 0
            afk_rewards.save()

            return Response({'status': True,
                             'coins_per_min': coins_per_min,
                             'dust_per_min': dust_per_min,
                             # 'exp_per_min': exp_per_min,
                             'last_collected_time': last_collected_time,
                             'coins': coins,
                             'dust': dust,
                             # 'exp': exp
                             'unclaimed_gold': afk_rewards.unclaimed_gold,
                             'unclaimed_dust': afk_rewards.unclaimed_dust,
                             'unclaimed_shards': afk_rewards.unclaimed_shards,
                             'runes_left': afk_rewards.runes_left
                             })

        return Response({'status': True,
                         'coins_per_min': coins_per_min,
                         'dust_per_min': dust_per_min,
                         # 'exp_per_min': exp_per_min,
                         'last_collected_time': last_collected_time,
                         'coins': coins,
                         'dust': dust,
                         # 'exp': exp
                         })


class CollectAFKRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        inventory = request.user.inventory
        last_collected_time = inventory.last_collected_rewards
        dungeon_progress = DungeonProgress.objects.get(user=request.user)

        vip_level = vip_exp_to_level(request.user.userinfo.vip_exp)
        time = afk_secs_since_last_datetime(last_collected_time, vip_level)
        coins_per_second = afk_coins_per_min(dungeon_progress.campaign_stage) / 60
        dust_per_second = afk_dust_per_min(dungeon_progress.campaign_stage) / 60

        coins = math.floor(time * coins_per_second * afk_rewards_multiplier_vip(vip_level))
        dust = math.floor(time * dust_per_second * afk_rewards_multiplier_vip(vip_level))
        # exp = time * afk_exp_per_min(dungeon_progress.stage_id)

        if server.is_server_version_higher('0.5.0'):
            inventory.coins += request.user.afkreward.unclaimed_gold
            inventory.dust += request.user.afkreward.unclaimed_dust
            inventory.rare_shards += request.user.afkreward.unclaimed_shards[0]
            inventory.epic_shards += request.user.afkreward.unclaimed_shards[1]
            inventory.legendary_shards += request.user.afkreward.unclaimed_shards[2]

            request.user.afkreward.unclaimed_gold = 0
            request.user.afkreward.unclaimed_dust = 0
            request.user.afkreward.unclaimed_shards = default_afk_shard_list()
            request.user.afkreward.unclaimed_converted_runes = 0
            request.user.afkreward.save()
        else:
            inventory.last_collected_rewards = datetime.now(timezone.utc)
            inventory.coins += coins
            inventory.dust += dust

        # request.user.userinfo.player_exp += exp
        # request.user.userinfo.save()

        inventory.save()

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
