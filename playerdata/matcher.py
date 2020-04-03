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
from .datagetter import ItemSchema

class FullCharacterSchema(Schema):
    char_id = fields.Int()
    user_id = fields.Int(attribute='user_id')
    char_type = fields.Int(attribute='char_type_id')
    exp = fields.Int()
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

class UserInfoSchema(Schema):
    user_id = fields.Int(attribute='user_id')
    elo = fields.Int()
    name = fields.Str() 
    default_placement = fields.Nested(PlacementSchema) 

class MatcherView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        return Response({'test':'value'})

class GetUserView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = GetUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_user = serializer.validated_data['target_user']
        target_user_info = UserInfoSchema(UserInfo.objects.select_related('default_placement__char_1').get(user_id=target_user))
        return Response(target_user_info.data)
