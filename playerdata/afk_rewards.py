from datetime import datetime, timezone
import math

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from playerdata.formulas import afk_coins_per_min, afk_gems_per_min, afk_exp_per_min
from playerdata.models import DungeonProgress
from playerdata.models import User


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

        coins_per_min = afk_coins_per_min(dungeon_progress.stage_id)
        gems_per_min = afk_gems_per_min(dungeon_progress.stage_id)
        # exp_per_min = afk_exp_per_min(dungeon_progress.stage_id)

        coins = time * coins_per_min
        gems = math.floor(time * gems_per_min)
        # exp = time * exp_per_min

        return Response({'coins_per_min': coins_per_min, 'gems_per_min': gems_per_min,
                         # 'exp_per_min': exp_per_min,
                         'last_collected_time': last_collected_time,
                         'coins': coins, 'gems': gems,
                         # 'exp': exp
                         })


class CollectAFKRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        inventory = request.user.inventory
        last_collected_time = inventory.last_collected_rewards
        dungeon_progress = DungeonProgress.objects.get(user=request.user)

        time = mins_since_last_collection(last_collected_time)
        coins = time * afk_coins_per_min(dungeon_progress.stage_id)
        gems = math.floor(time * afk_gems_per_min(dungeon_progress.stage_id))
        # exp = time * afk_exp_per_min(dungeon_progress.stage_id)

        inventory.last_collected_rewards = datetime.now(timezone.utc)
        inventory.coins += coins
        inventory.gems += gems
        inventory.save()

        # request.user.userinfo.player_exp += exp
        # request.user.userinfo.save()

        return Response({'status': True, 'coins': coins, 'gems': gems})
