import random

from django.db import transaction
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata import constants, matcher
from playerdata.models import UserInfo


######################
# Redis List Functions (https://redis.io/commands#list)
# With these queues we've chosen to do right pushes and left pops

def get_opponent_queue_key(user_id):
    return "opp_" + str(user_id)


def get_recently_seen_key(user_id):
    return "seen_" + str(user_id)


def next_opponent(user):
    opponent_queue_key = get_opponent_queue_key(user.id)
    recently_seen_key = get_recently_seen_key(user.id)

    r = get_redis_connection("default")

    # push more opponents into the queue if less than 10
    if r.llen(opponent_queue_key) < 10:
        exclude_list = r.lrange(recently_seen_key, 0, 10)
        user_ids = get_opponents_list(user, exclude_list)
        r.rpush(opponent_queue_key, *user_ids)

    # pop the current opponent off the queue and push it into recently seen
    opponent_id = r.lpop(opponent_queue_key)
    r.rpush(recently_seen_key, opponent_id)

    if r.llen(recently_seen_key) > 10:
        r.lpop(recently_seen_key)


def get_random_opponents(self_user_id, num_opponents, min_elo, max_elo, exclude_list=None):
    if exclude_list is None:
        exclude_list = []
    exclude_list.append(self_user_id)

    users = UserInfo.objects.filter(elo__gte=min_elo, elo__lte=max_elo) \
                    .exclude(user_id__in=exclude_list) \
                    .values_list('user_id', flat=True)[:100]

    return random.sample(list(users), min(len(users), num_opponents))


def get_opponents_list(user, exclude_list):
    cur_elo = user.userinfo.elo
    user_ids = []
    search_count = 1

    # loop until we have at least 10 users in the queue
    # each loop increases the elo bounds we search in
    while len(user_ids) < 10:
        bound = search_count * constants.MATCHER_INCREASE_RANGE + constants.MATCHER_START_RANGE
        user_ids = get_random_opponents(user.id, constants.MATCHER_DEFAULT_COUNT,
                                        cur_elo - bound, cur_elo + bound, exclude_list)
        search_count += 1

    return user_ids


class GetOpponentView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        r = get_redis_connection("default")
        opponent_queue_key = get_opponent_queue_key(request.user.id)

        # push more opponents into the queue
        if r.llen(opponent_queue_key) < 10:
            next_opponent(request.user)

        opponent_id = int(r.lindex(opponent_queue_key, 0))
        query = matcher.userinfo_preloaded().filter(user_id=opponent_id).first()
        enemies = matcher.UserInfoSchema(query)

        return Response(enemies.data)
