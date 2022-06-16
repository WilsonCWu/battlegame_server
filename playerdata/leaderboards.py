from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_404_NOT_FOUND,
)
from rest_framework.views import APIView

from playerdata.models import Clan2
from playerdata.models import UserInfo
from .matcher import LightUserInfoSchema
from .serializers import ValueSerializer
from .social import ClanSchema


def pvp_ranking_key():
    return "pvp_ranking"


def clan_ranking_key():
    return "clan_ranking"


# REDIS Sorted Sets
# https://redis.io/topics/data-types-intro#redis-sorted-sets
# Functions: ZADD, ZREVRANK (reverse rank)

def update_redis_ranking(user_id, elo, key):
    r = get_redis_connection("default")
    r.zadd(key, {user_id: elo})  # user needs to be added in a dict


# Expected format
# users_dict: {user_id: elo, ... }
def bulk_update_redis_ranking(users_dict, key):
    r = get_redis_connection("default")
    r.zadd(key, users_dict)


def get_self_rank(user_id):
    r = get_redis_connection("default")
    ranking_key = pvp_ranking_key()

    rank = r.zrevrank(ranking_key, user_id)
    if rank is None:
        r.zadd(ranking_key, {user_id: 0})
        rank = r.zrevrank(ranking_key, user_id)

    return rank + 1  # zero indexed, add 1


def get_clan_rank(clan_name):
    r = get_redis_connection("default")
    ranking_key = clan_ranking_key()

    rank = r.zrevrank(ranking_key, clan_name)
    return rank + 1


class GetLeaderboardView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leaderboard_type = serializer.validated_data['value']

        if leaderboard_type == 'solo_top_100':
            top_player_set = UserInfo.objects.all().order_by('-elo')[:100]
            players = LightUserInfoSchema(top_player_set, many=True)
            return Response({'status': True, 'players': players.data, 'self_rank': get_self_rank(request.user.id)})

        if leaderboard_type == 'clan_top_100':
            top_clan_set = Clan2.objects.all().order_by('-elo')[:100]
            clans = ClanSchema(top_clan_set, many=True)
            return Response({'status': True, 'clans': clans.data})

        if leaderboard_type == 'moevasion_top_100':
            top_moevasion_set = UserInfo.objects.all().order_by('-best_moevasion_stage')[:100]
            players = LightUserInfoSchema(top_moevasion_set, many=True)
            return Response({'status': True, 'players': players.data})
        else:
            return Response({'status': True, 'reason': 'leaderboard ' + leaderboard_type + ' does not exist',
                             'detail': 'leaderboard ' + leaderboard_type + ' does not exist'},
                            status=HTTP_404_NOT_FOUND)
