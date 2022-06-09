import math
from datetime import datetime, timedelta
from typing import List
from functools import lru_cache

from django.contrib.auth.models import User
from django.db.transaction import atomic
from marshmallow import fields
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema

from playerdata import constants, chests, formulas, server, tier_system
from playerdata.models import EloRewardTracker, SeasonReward, UserInfo, ChampBadgeTracker, ClanSeasonReward
from playerdata.serializers import IntSerializer


# TODO: Tune rewards
def get_clan_season_rewards(rank: int):
    rewards = []

    rewards.append(chests.ChestReward('relic_stone', rank * 55 + 200))

    return rewards


class GetClanSeasonRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        clean_season_reward = request.user.clanseasonreward

        return Response({'status': True,
                         'is_claimed': clean_season_reward.is_claimed,
                         'rank': clean_season_reward.tier_rank,
                         'expiration_date': tier_system.get_season_expiration_date()})


class ClaimClanSeasonRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        season_reward = request.user.clanseasonreward
        if season_reward.is_claimed:
            return Response({'status': False, 'reason': 'clan season reward already claimed!'})

        rewards = get_clan_season_rewards(season_reward.rank)
        chests.award_chest_rewards(request.user, rewards)

        season_reward.is_claimed = True
        season_reward.save()

        return Response({'status': True, 'rewards': chests.ChestRewardSchema(rewards, many=True).data})


# TODO: might need to track clan ranks on redis just like players, should be very doable
def get_clan_rank():
    return 1


def clan_season_cron():
    seasons = ClanSeasonReward.objects.select_related('user__userinfo').all()

    for season in seasons:
        if hasattr(season.user, 'userinfo'):
            season.rank = get_clan_rank()
            season.is_claimed = False

    ClanSeasonReward.objects.bulk_update(seasons, ['rank', 'is_claimed'])
