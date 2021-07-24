from datetime import datetime, timezone
import math

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from playerdata.formulas import afk_coins_per_min, afk_exp_per_min, afk_dust_per_min, vip_exp_to_level
from playerdata.models import DungeonProgress


def mins_since_last_collection(last_collected_time):
    now_time = datetime.now(timezone.utc)
    elapsed = now_time - last_collected_time
    elapsed_mins = int(elapsed.total_seconds() / 60)
    return min(12 * 60, elapsed_mins)


class GetAFKRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        dungeon_progress = DungeonProgress.objects.get(user=request.user)
        last_collected_time = request.user.inventory.last_collected_rewards

        time = mins_since_last_collection(last_collected_time)

        coins_per_min = afk_coins_per_min(dungeon_progress.campaign_stage)
        dust_per_min = afk_dust_per_min(dungeon_progress.campaign_stage)
        # exp_per_min = afk_exp_per_min(dungeon_progress.stage_id)

        vip_level = vip_exp_to_level(request.user.userinfo.vip_exp)
        coins = math.floor(time * coins_per_min * afk_rewards_multiplier_vip(vip_level))
        dust = math.floor(time * dust_per_min * afk_rewards_multiplier_vip(vip_level))
        # exp = time * exp_per_min

        return Response({'coins_per_min': coins_per_min,
                         'dust_per_min': dust_per_min,
                         # 'exp_per_min': exp_per_min,
                         'last_collected_time': last_collected_time,
                         'coins': coins,
                         'dust': dust,
                         # 'exp': exp
                         })


class CollectAFKRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        inventory = request.user.inventory
        last_collected_time = inventory.last_collected_rewards
        dungeon_progress = DungeonProgress.objects.get(user=request.user)

        time = mins_since_last_collection(last_collected_time)
        vip_level = vip_exp_to_level(request.user.userinfo.vip_exp)
        coins = math.floor(time * afk_coins_per_min(dungeon_progress.campaign_stage) * afk_rewards_multiplier_vip(vip_level))
        dust = math.floor(time * afk_dust_per_min(dungeon_progress.campaign_stage) * afk_rewards_multiplier_vip(vip_level))
        # exp = time * afk_exp_per_min(dungeon_progress.stage_id)

        inventory.last_collected_rewards = datetime.now(timezone.utc)
        inventory.coins += coins
        inventory.dust += dust
        inventory.save()

        # request.user.userinfo.player_exp += exp
        # request.user.userinfo.save()

        return Response({'status': True, 'coins': coins, 'dust': dust})


def afk_rewards_multiplier_vip(level: int):
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
