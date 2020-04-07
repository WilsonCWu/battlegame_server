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

from playerdata.models import Placement
from playerdata.models import UserInfo
from playerdata.models import Character
from playerdata.models import Item
from .serializers import GetUserSerializer
from .serializers import GetOpponentsSerializer
from .datagetter import ItemSchema

class FullCharacterSchema(Schema):
    char_id = fields.Int()
    user_id = fields.Int(attribute='user_id')
    char_type = fields.Int(attribute='char_type_id')
    level = fields.Int()
    prestige = fields.Int()
    weapon = fields.Nested(ItemSchema)

class PlacementSchema(Schema):
    placement_id = fields.Int() 
    pos_1 = fields.Int() 
    char_1 = fields.Nested(FullCharacterSchema)
    pos_2 = fields.Int() 
    char_2 = fields.Nested(FullCharacterSchema)
    pos_3 = fields.Int() 
    char_3 = fields.Nested(FullCharacterSchema)
    pos_4 = fields.Int() 
    char_4 = fields.Nested(FullCharacterSchema)
    pos_5 = fields.Int() 
    char_5 = fields.Nested(FullCharacterSchema)

class TeamSchema(Schema):
    team_id = fields.Int() 
    char_1 = fields.Nested(FullCharacterSchema)
    char_2 = fields.Nested(FullCharacterSchema)
    char_3 = fields.Nested(FullCharacterSchema)
    char_4 = fields.Nested(FullCharacterSchema)
    char_5 = fields.Nested(FullCharacterSchema)
    char_6 = fields.Nested(FullCharacterSchema)

class UserInfoSchema(Schema):
    user_id = fields.Int(attribute='user_id')
    elo = fields.Int()
    name = fields.Str() 
    default_placement = fields.Nested(PlacementSchema) 
    team = fields.Nested(TeamSchema)

class MatcherView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({'test':'value'})

class GetUserView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        query = UserInfo.objects.select_related('team__char_1__weapon') \
                                .select_related('team__char_2__weapon') \
                                .select_related('team__char_3__weapon') \
                                .select_related('team__char_4__weapon') \
                                .select_related('team__char_5__weapon') \
                                .select_related('team__char_6__weapon') \
                                .get(user_id=request.user.id)
        user_info = UserInfoSchema(query, exclude=('default_placement',))
        return Response(user_info.data)

    def post(self, request):
        serializer = GetUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data['target_user']
        query = UserInfo.objects.select_related('default_placement__char_1__weapon') \
                                .select_related('default_placement__char_2__weapon') \
                                .select_related('default_placement__char_3__weapon') \
                                .select_related('default_placement__char_4__weapon') \
                                .select_related('default_placement__char_5__weapon') \
                                .get(user_id=target_user)
        target_user_info = UserInfoSchema(query, exclude=('team',))
        return Response(target_user_info.data)

class GetOpponentsView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = GetOpponentsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        search_count = serializer.validated_data['search_count']
        cur_elo = request.user.userinfo.elo
        query = UserInfo.objects.select_related('default_placement__char_1__weapon') \
                                .select_related('default_placement__char_2__weapon') \
                                .select_related('default_placement__char_3__weapon') \
                                .select_related('default_placement__char_4__weapon') \
                                .select_related('default_placement__char_5__weapon') \
                                .filter(elo__gte=cur_elo-200, elo__lte=cur_elo+200) \
                                [:30]
        enemies = UserInfoSchema(query, exclude=('team',), many=True)
        return Response({'users':enemies.data})
        

