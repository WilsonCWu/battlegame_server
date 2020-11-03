import random
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_200_OK,
)
from django.contrib.auth import authenticate
from django.http import JsonResponse

from rest_marshmallow import Schema, fields

from playerdata import constants, formulas
from playerdata.models import Placement
from playerdata.models import UserInfo
from playerdata.models import Character
from playerdata.models import Item
from playerdata.models import Placement

from .serializers import GetUserSerializer
from .serializers import GetOpponentsSerializer
from .serializers import UpdatePlacementSerializer
from .inventory import CharacterSchema


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
    elo = fields.Int()
    tourney_elo = fields.Int()
    prev_tourney_elo = fields.Int()
    name = fields.Str()
    description = fields.Str()
    profile_picture = fields.Int()
    num_wins = fields.Int(attribute='user.userstats.num_wins')
    num_games = fields.Int(attribute='user.userstats.num_games')
    time_started = fields.Str(attribute='user.userstats.time_started')
    default_placement = fields.Nested(PlacementSchema)
    clan = fields.Str(attribute='clanmember.clan_id')
    player_level = fields.Function(lambda userinfo: formulas.exp_to_level(userinfo.player_exp))


class MatcherView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({'test': 'value'})


class GetUserView(APIView):
    permission_classes = (IsAuthenticated,)

    # TODO(yanke): do we need equippables for these queries?
    def get(self, request):
        query = UserInfo.objects.select_related('default_placement__char_1__weapon') \
            .select_related('default_placement__char_2__weapon') \
            .select_related('default_placement__char_3__weapon') \
            .select_related('default_placement__char_4__weapon') \
            .select_related('default_placement__char_5__weapon') \
            .select_related('clanmember') \
            .select_related('user__userstats') \
            .get(user_id=request.user.id)
        user_info = UserInfoSchema(query)
        return Response(user_info.data)

    def post(self, request):
        """Post returns the user view of another user."""
        serializer = GetUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data['target_user']
        # TODO(yanke): this query is about to get ugly with the item preloads.
        query = UserInfo.objects.select_related('default_placement__char_1__weapon') \
            .select_related('default_placement__char_2__weapon') \
            .select_related('default_placement__char_3__weapon') \
            .select_related('default_placement__char_4__weapon') \
            .select_related('default_placement__char_5__weapon') \
            .select_related('user__userstats') \
            .get(user_id=target_user)
        target_user_info = UserInfoSchema(query)
        return Response(target_user_info.data)


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
        
        query = UserInfo.objects.select_related('default_placement__char_1__weapon') \
                    .select_related('default_placement__char_2__weapon') \
                    .select_related('default_placement__char_3__weapon') \
                    .select_related('default_placement__char_4__weapon') \
                    .select_related('default_placement__char_5__weapon') \
                    .filter(user_id__in=user_ids) \

        enemies = UserInfoSchema(query, many=True)
        return Response({'users': enemies.data})


class PlacementsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        placements = Placement.objects.filter(user=request.user, is_tourney=False)
        return Response({'placements': [PlacementSchema(p).data for p in placements]})

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
