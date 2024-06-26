import random

from django.db import transaction
from django_redis import get_redis_connection
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata import constants, matcher, server
from playerdata.models import UserInfo


# Pops the current opponent off of the queue
# returns the next opponent
# replenishes the queue if it was empty from the pop
def pop_pvp_queue(user):
    r = get_redis_connection("default")

    opponent_queue_key = build_opponent_queue_key(user.id)
    recently_seen_key = build_recently_seen_key(user.id)

    # push more opponents into the queue if last one
    if r.llen(opponent_queue_key) <= 1:
        add_opponents_to_queue(r, user, opponent_queue_key, recently_seen_key)

    # pop the current opponent off the queue and push it into recently seen
    opponent_id = r.lpop(opponent_queue_key)
    r.rpush(recently_seen_key, opponent_id)

    if is_over_queue_limit(r, recently_seen_key, RECENTLY_SEEN_QUEUE_LIMIT):
        r.lpop(recently_seen_key)

    # expire the keys after 6 hours
    r.expire(opponent_queue_key, 21600)
    r.expire(recently_seen_key, 21600)

    return get_current_opponent_id(r, opponent_queue_key)


######################
# Redis List Functions (https://redis.io/commands#list)
# With these queues we've chosen to do right pushes and left pops

RECENTLY_SEEN_QUEUE_LIMIT = 10


def build_opponent_queue_key(user_id):
    return "opp_" + str(user_id)


def build_recently_seen_key(user_id):
    return "seen_" + str(user_id)


def is_over_queue_limit(r, key, limit):
    return r.llen(key) > limit


def get_current_opponent_id(r, key):
    return int(r.lindex(key, 0))


def get_redis_list(r, key, MAX_SIZE):
    return r.lrange(key, 0, MAX_SIZE)


def add_opponents_to_queue(r, user, opponent_queue_key, recently_seen_key):
    # hardcode queue the first 5 opponents
    if user.userstats.num_games == 0:
        r.rpush(opponent_queue_key, 86, 87, 88, 100, 101)
        return

    exclude_list = get_redis_list(r, recently_seen_key, RECENTLY_SEEN_QUEUE_LIMIT)
    user_ids = get_opponents_list(user, exclude_list)
    r.rpush(opponent_queue_key, *user_ids)


def _get_opponents_within_elo(cur_elo, search_count, exclude_list):
    bound = search_count * constants.MATCHER_INCREASE_RANGE + constants.MATCHER_START_RANGE
    min_elo = cur_elo - bound
    max_elo = cur_elo + bound

    if max_elo <= 150:
        return UserInfo.objects.filter(elo__gte=min_elo, elo__lte=max_elo, is_bot=True) \
            .exclude(user_id__in=exclude_list) \
            .values_list('user_id', flat=True)[:1000]
    else:
        return UserInfo.objects.filter(elo__gte=min_elo, elo__lte=max_elo,) \
            .exclude(user_id__in=exclude_list) \
            .values_list('user_id', flat=True)[:1000]


def get_opponents_list(user, exclude_list):
    cur_elo = user.userinfo.elo
    search_count = 1
    num_opponents = 7
    exclude_list.append(user.id)

    # loop until we have at least NUM_OPPONENTS users in the queue
    # each loop increases the elo bounds we search in
    users = _get_opponents_within_elo(cur_elo, search_count, exclude_list)
    while users.count() < num_opponents:
        search_count += 1
        users = _get_opponents_within_elo(cur_elo, search_count, exclude_list)

    return random.sample(list(users), min(len(users), num_opponents))


class GetOpponentView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        r = get_redis_connection("default")
        opponent_queue_key = build_opponent_queue_key(request.user.id)
        recently_seen_key = build_recently_seen_key(request.user.id)

        # push more opponents into the queue
        if r.llen(opponent_queue_key) == 0:
            add_opponents_to_queue(r, request.user, opponent_queue_key, recently_seen_key)

        opponent_id = get_current_opponent_id(r, opponent_queue_key)
        query = matcher.userinfo_preloaded().filter(user_id=opponent_id).first()
        enemies = matcher.UserInfoSchema(query)
        if server.is_server_version_higher('0.5.0'):
            return Response({'status': True, 'user_info': enemies.data})
        return Response(enemies.data)
