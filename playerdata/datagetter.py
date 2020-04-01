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

from playerdata.models import BaseCharacter

class BaseCharacterSchema(Schema):
    char_id = fields.Int() 
    name = fields.Str()
    health = fields.Int()
    mana = fields.Int()
    speed = fields.Int()
    attack = fields.Int()
    ar = fields.Int()
    mr = fields.Int()
    attack_range = fields.Int()
    rarity = fields.Int()
    crit_chance = fields.Int()

class BaseInfoView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        serializer = BaseCharacterSchema(BaseCharacter.objects.all(), many=True)
        return Response(serializer.data)
