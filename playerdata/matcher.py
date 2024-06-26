import random
import secrets
from collections import defaultdict

from django.contrib.auth import get_user_model
from django.db import transaction
from random_username.generate import generate_username
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import constants, formulas, server
from playerdata.models import BaseCharacter
from playerdata.models import Character
from playerdata.models import Match, MatchReplay, ServerStatus
from playerdata.models import Placement
from playerdata.models import UserInfo
from .inventory import CharacterSchema
from .serializers import GetMatchHistorySerializer
from .serializers import GetOpponentsSerializer
from .serializers import GetUserSerializer
from .serializers import IntSerializer
from .serializers import UpdatePlacementSerializer


class PlacementSchema(Schema):
    placement_id = fields.Int()
    pos_1 = fields.Int()
    char_1 = fields.Nested(CharacterSchema)
    pos_2 = fields.Int()
    char_2 = fields.Nested(CharacterSchema)
    pos_3 = fields.Int()
    char_3 = fields.Nested(CharacterSchema)
    pos_4 = fields.Int()
    char_4 = fields.Nested(CharacterSchema)
    pos_5 = fields.Int()
    char_5 = fields.Nested(CharacterSchema)


class UserInfoSchema(Schema):
    user_id = fields.Int(attribute='user_id')
    highest_elo = fields.Int()
    highest_season_elo = fields.Int()
    elo = fields.Int()
    tier_rank = fields.Int()
    best_moevasion_stage = fields.Int()
    best_daily_dungeon_stage = fields.Int()
    tourney_elo = fields.Int()
    prev_tourney_elo = fields.Int()
    name = fields.Str()
    description = fields.Str()
    profile_picture = fields.Int()
    num_wins = fields.Int(attribute='user.userstats.num_wins')
    num_games = fields.Int(attribute='user.userstats.num_games')
    time_started = fields.Str(attribute='user.userstats.time_started')
    longest_win_streak = fields.Int(attribute='user.userstats.longest_win_streak')
    daily_wins = fields.Int(attribute='user.userstats.daily_wins')
    daily_games = fields.Int(attribute='user.userstats.daily_games')
    campaign_stage = fields.Int(attribute='user.dungeonprogress.campaign_stage')
    total_damage = fields.Function(lambda userinfo: defaultdict(int, userinfo.user.userstats.cumulative_stats)[str(constants.DAMAGE_DEALT)])

    default_placement = fields.Nested(PlacementSchema)
    clan = fields.Function(lambda userinfo: userinfo.clanmember.clan2.name if userinfo.clanmember.clan2 else '')
    player_level = fields.Function(lambda userinfo: formulas.exp_to_level(userinfo.player_exp))
    vip_exp = fields.Function(lambda userinfo: formulas.vip_exp_to_level(userinfo.vip_exp))
    is_monthly_sub = fields.Bool()
    last_login = fields.DateTime()


# This is a light-weight Userinfo Schema for showing users in a list
class LightUserInfoSchema(Schema):
    user_id = fields.Int(attribute='user_id')
    elo = fields.Int()
    best_moevasion_stage = fields.Int()
    name = fields.Str()
    profile_picture = fields.Int()
    # TODO: this is leading to a lot of n+1 calls, we need to optimize / do
    # this better.
    clan = fields.Function(lambda userinfo: userinfo.clanmember.clan2.name if userinfo.clanmember.clan2 else '')


class LightUserSchema(Schema):
    userinfo = fields.Nested(LightUserInfoSchema)


class MatchHistorySchema(Schema):
    id = fields.Int()
    attacker = fields.Nested(LightUserSchema)
    defender = fields.Nested(LightUserSchema)
    is_win = fields.Bool()
    uploaded_at = fields.DateTime()
    original_attacker_elo = fields.Int()
    updated_attacker_elo = fields.Int()
    original_defender_elo = fields.Int()
    updated_defender_elo = fields.Int()
    has_replay = fields.Function(lambda m: hasattr(m, 'matchreplay'))


class MatchReplaySchema(Schema):
    id = fields.Int(attribute='match.id')
    attacker = fields.Nested(LightUserSchema, attribute='match.attacker')
    defender = fields.Nested(LightUserSchema, attribute='match.defender')
    is_win = fields.Bool(attribute='match.is_win')
    seed = fields.Int()
    attacking_team = fields.Str()
    defending_team = fields.Str()


class MatcherView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({'test': 'value'})


def userinfo_with_items():
    return UserInfo.objects \
        .select_related('default_placement__char_1__weapon') \
        .select_related('default_placement__char_2__weapon') \
        .select_related('default_placement__char_3__weapon') \
        .select_related('default_placement__char_4__weapon') \
        .select_related('default_placement__char_5__weapon') \
        .select_related('default_placement__char_1__hat') \
        .select_related('default_placement__char_2__hat') \
        .select_related('default_placement__char_3__hat') \
        .select_related('default_placement__char_4__hat') \
        .select_related('default_placement__char_5__hat') \
        .select_related('default_placement__char_1__armor') \
        .select_related('default_placement__char_2__armor') \
        .select_related('default_placement__char_3__armor') \
        .select_related('default_placement__char_4__armor') \
        .select_related('default_placement__char_5__armor') \
        .select_related('default_placement__char_1__boots') \
        .select_related('default_placement__char_2__boots') \
        .select_related('default_placement__char_3__boots') \
        .select_related('default_placement__char_4__boots') \
        .select_related('default_placement__char_5__boots') \
        .select_related('default_placement__char_1__trinket_1') \
        .select_related('default_placement__char_2__trinket_1') \
        .select_related('default_placement__char_3__trinket_1') \
        .select_related('default_placement__char_4__trinket_1') \
        .select_related('default_placement__char_5__trinket_1') \
        .select_related('default_placement__char_1__trinket_2') \
        .select_related('default_placement__char_2__trinket_2') \
        .select_related('default_placement__char_3__trinket_2') \
        .select_related('default_placement__char_4__trinket_2') \
        .select_related('default_placement__char_5__trinket_2')


def userinfo_preloaded():
    return userinfo_with_items() \
        .select_related('clanmember') \
        .select_related('user__userstats')\
        .select_related('user__dungeonprogress')


class GetUserView(APIView):
    permission_classes = (IsAuthenticated,)

    @staticmethod
    def _get_userinfo(user_id):
        query = userinfo_preloaded() \
            .get(user_id=user_id)
        return UserInfoSchema(query)

    # TODO(yanke): split up usecases for user infos that need placements and
    # all its equips.
    def get(self, request):
        if server.is_server_version_higher('0.5.0'):
            return Response({'status': True, 'user_info': GetUserView._get_userinfo(request.user.id).data})
        return Response(GetUserView._get_userinfo(request.user.id).data)

    def post(self, request):
        """Post returns the user view of another user."""
        serializer = GetUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data['target_user']
        if server.is_server_version_higher('0.5.0'):
            return Response({'status': True, 'user_info': GetUserView._get_userinfo(target_user).data})
        return Response(GetUserView._get_userinfo(target_user).data)


class GetOpponentsView(APIView):
    permission_classes = (IsAuthenticated,)

    # will return UP TO numOpponents
    @staticmethod
    def _get_random_opponents(self_user_id, num_opponents, min_elo, max_elo):
        users = UserInfo.objects.filter(elo__gte=min_elo, elo__lte=max_elo) \
                        .exclude(user_id = self_user_id) \
                        .values_list('user_id', flat=True)[:100]
        return random.sample(list(users), min(len(users), num_opponents))

    def post(self, request):
        serializer = GetOpponentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        search_count = serializer.validated_data['search_count']

        # get some random users, and expand range if the search_count is going up
        cur_elo = request.user.userinfo.elo
        bound = search_count*constants.MATCHER_INCREASE_RANGE+constants.MATCHER_START_RANGE
        user_ids = GetOpponentsView._get_random_opponents(request.user.id, constants.MATCHER_DEFAULT_COUNT, cur_elo - bound, cur_elo + bound)

        query = userinfo_preloaded() \
            .filter(user_id__in=user_ids)

        enemies = UserInfoSchema(query, many=True)
        return Response({'status': True, 'users': enemies.data})


class PlacementsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        placements = Placement.objects.filter(user=request.user, is_tourney=False)
        return Response({'status': True, 'placements': [PlacementSchema(p).data for p in placements]})

    def post(self, request):
        serializer = UpdatePlacementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if 'placement_id' in serializer.validated_data:
            id = serializer.validated_data['placement_id']
            placement = Placement.objects.get(placement_id=id)
            if placement.user != request.user:
                return Response({'status': False, 'reason': 'user does not own the placement'})

            self._update_placement(placement, serializer)
            return Response({'status': True})
        else:
            # TODO(yanke): currently limit the user to 3 placements. In the
            # future we can expand slots like rune pages for P2W players.
            if Placement.objects.filter(user=request.user, is_tourney=False).count() >= 3:
                return Response({'status': False, 'reason': 'user already has the max 3 placement'})

            placement = self._new_placement(request.user, serializer)
            return Response({'status': True, 'placement_id': placement.placement_id})

    def _update_placement(self, placement, serializer):
        characters = serializer.validated_data['characters']
        characters = [cid if cid != -1 else None for cid in characters]
        positions = serializer.validated_data['positions']

        placement.char_1_id=characters[0]
        placement.char_2_id=characters[1]
        placement.char_3_id=characters[2]
        placement.char_4_id=characters[3]
        placement.char_5_id=characters[4]
        placement.pos_1=positions[0]
        placement.pos_2=positions[1]
        placement.pos_3=positions[2]
        placement.pos_4=positions[3]
        placement.pos_5=positions[4]
        placement.save()

    def _new_placement(self, user, serializer):
        characters = serializer.validated_data['characters']
        characters = [cid if cid != -1 else None for cid in characters]
        positions = serializer.validated_data['positions']

        return Placement.objects.create(
            user=user,
            char_1_id=characters[0],
            char_2_id=characters[1],
            char_3_id=characters[2],
            char_4_id=characters[3],
            char_5_id=characters[4],
            pos_1=positions[0],
            pos_2=positions[1],
            pos_3=positions[2],
            pos_4=positions[3],
            pos_5=positions[4],
        )


class GetMatchHistoryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = GetMatchHistorySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        attacker_query = Match.objects.filter(attacker=request.user) \
            .select_related('attacker__userinfo') \
            .select_related('defender__userinfo') \
            .select_related('matchreplay')
        defender_query = Match.objects.filter(defender=request.user) \
            .select_related('attacker__userinfo') \
            .select_related('defender__userinfo') \
            .select_related('matchreplay')

        limit = serializer.validated_data['count']
        query = (attacker_query | defender_query).order_by('-uploaded_at')[:limit]
        matches = MatchHistorySchema(query, many=True)

        return Response({'status': True, 'matches': matches.data})


class GetReplayView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        match_q = Match.objects.filter(id=serializer.validated_data['value'])
        if not match_q:
            return Response({'status': False, 'reason': 'match expired or does not exist'})

        match = match_q[0]
        if ServerStatus.latest_version() != match.version:
            return Response({'status': False, 'reason': 'replay version out of date'})

        replay_q = MatchReplay.objects.filter(match=match)
        if not replay_q:
            return Response({'status': False, 'reason': 'replay expired for match'})

        replay = MatchReplaySchema(replay_q[0])
        return Response({'status': True, 'replay': replay.data})


# Same as above, but returns the match object instead of a matchreplay
class GetReplayMatchView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        match = Match.objects.filter(id=serializer.validated_data['value']).first()
        if match is None:
            return Response({'status': False, 'reason': 'match expired or does not exist'})
        if ServerStatus.latest_version() != match.version:
            return Response({'status': False, 'reason': 'replay version out of date'})

        match_export = MatchHistorySchema(match)
        return Response({'status': True, 'match': match_export.data})


class BotsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        query = UserInfo.objects.filter(is_bot=True)\
            .select_related('default_placement__char_1__weapon') \
            .select_related('default_placement__char_2__weapon') \
            .select_related('default_placement__char_3__weapon') \
            .select_related('default_placement__char_4__weapon') \
            .select_related('default_placement__char_5__weapon') \
            .select_related('clanmember') \
            .select_related('user__userstats') \

        user_info = UserInfoSchema(query, many=True)
        return Response({'users': user_info.data})


# creates n users
def create_users(num_users):
    users = []
    for i in range(num_users):
        latest_id = get_user_model().objects.latest('id').id + 1
        password = secrets.token_urlsafe(35)

        user = get_user_model().objects.create_user(username=latest_id, password=password)
        users.append(user)
    return users


@transaction.atomic
def _generate_bots(num_bots_per_user, elo, char_levels, num_chars=5):
    bot_users = create_users(num_bots_per_user)

    for bot_user in bot_users:
        bot_userinfo = UserInfo.objects.get(user=bot_user)
        bot_userinfo.name = generate_username(1)[0]
        bot_userinfo.elo = random.randint(max(0, elo - 50), elo + 50)
        bot_userinfo.is_bot = True
        bot_userinfo.save()

        # random char
        base_chars = BaseCharacter.objects.filter(rollable=True)
        chosen_chars = random.sample(list(base_chars), num_chars)

        bot_placement = Placement.objects.get(user=bot_user)

        available_pos_frontline = [*constants.FRONTLINE_POS]
        available_pos_backline = [*constants.BACKLINE_POS]

        for i in range(0, num_chars):
            new_char = Character.objects.create(user=bot_user, char_type=chosen_chars[i])
            if new_char.char_type in constants.FRONTLINE_POS:
                position = random.choice(available_pos_frontline)
                available_pos_frontline.remove(position)
            else:
                position = random.choice(available_pos_backline)
                available_pos_backline.remove(position)

            if i == 0:
                level = char_levels[0]
                bot_placement.char_1 = new_char
                bot_placement.pos_1 = position
            elif i == 1:
                level = char_levels[1]
                bot_placement.char_2 = new_char
                bot_placement.pos_2 = position
            elif i == 2:
                level = char_levels[2]
                bot_placement.char_3 = new_char
                bot_placement.pos_3 = position
            elif i == 3:
                level = char_levels[3]
                bot_placement.char_4 = new_char
                bot_placement.pos_4 = position
            else:
                level = char_levels[4]
                bot_placement.char_5 = new_char
                bot_placement.pos_5 = position

            # generate a character +/- 10 levels of the user's char level
            level = random.randint(max(1, level - 10), min(240, level + 10))
            new_char.level = level
            new_char.save()

        bot_placement.save()


@transaction.atomic
def generate_bots_from_users(queryset):
    for userinfo in queryset:
        num_bots_per_user = 10

        placement = userinfo.default_placement
        num_chars = len(list(filter(None, [placement.char_1, placement.char_2,
                                           placement.char_3, placement.char_4, placement.char_5])))
        user_elo = userinfo.elo
        char_levels = [placement.char_1.level if placement.char_1 is not None else 1,
                       placement.char_2.level if placement.char_2 is not None else 1,
                       placement.char_3.level if placement.char_3 is not None else 1,
                       placement.char_4.level if placement.char_4 is not None else 1,
                       placement.char_5.level if placement.char_5 is not None else 1]

        _generate_bots(num_bots_per_user, user_elo, char_levels, num_chars)


@transaction.atomic
def generate_bots_bulk(start_elo, end_elo, num_bots_per_elo_range):
    for elo in range(start_elo, end_elo, 100):
        level = max(average_lvl_for_elo(elo) - 5, 10)
        char_levels = [level] * 5

        _generate_bots(num_bots_per_elo_range, elo, char_levels)


@transaction.atomic
def generate_bots_bulk_near_lvl(level, elo, num_bots):
    char_levels = [level] * 5
    _generate_bots(num_bots, elo, char_levels)


def get_avg_lvl_placement(placement):
    lvls = []
    if placement.char_1:
        lvls.append(placement.char_1.level)
    if placement.char_2:
        lvls.append(placement.char_2.level)
    if placement.char_3:
        lvls.append(placement.char_3.level)
    if placement.char_4:
        lvls.append(placement.char_4.level)
    if placement.char_5:
        lvls.append(placement.char_5.level)

    return sum(lvls) / len(lvls)


def average_lvl_for_elo(elo):
    userinfos = UserInfo.objects.filter(elo__gte=elo - 50, elo__lte=elo + 50).select_related(
        'default_placement__char_1') \
                    .select_related('default_placement__char_2') \
                    .select_related('default_placement__char_3') \
                    .select_related('default_placement__char_4') \
                    .select_related('default_placement__char_5')[:50]

    avg_lvls = []
    for userinfo in userinfos:
        lvl = get_avg_lvl_placement(userinfo.default_placement)
        avg_lvls.append(lvl)

    return round(sum(avg_lvls) / len(avg_lvls))
