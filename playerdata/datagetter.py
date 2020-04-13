import math

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
from playerdata.models import BaseItem
from playerdata.models import Character
from playerdata.models import Item
from playerdata.models import Inventory

from .serializers import LevelUpSerializer

class UserSchema(Schema):
    user_id = fields.Int(attribute='id')
    first_name = fields.Str()

class BaseCharacterSchema(Schema):
    char_type = fields.Int() 
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
    health_scale = fields.Int()
    attack_scale = fields.Int()
    ar_scale = fields.Int()
    mr_scale = fields.Int()

class BaseItemSchema(Schema):
    item_type = fields.Int()
    name = fields.Str()
    attack = fields.Int()
    penetration = fields.Int()
    attack_speed = fields.Int()
    rarity = fields.Int()
    cost = fields.Int()

class ItemSchema(Schema):
    item_id = fields.Int()
    user_id = fields.Int(attribute='user_id')
    item_type = fields.Int(attribute='item_type_id')
    exp = fields.Int()

class CharacterSchema(Schema):
    char_id = fields.Int()
    user_id = fields.Int(attribute='user_id')
    char_type = fields.Int(attribute='char_type_id')
    level = fields.Int()
    prestige = fields.Int()
    weapon_id = fields.Int(attribute='weapon_id')
    weapon = fields.Nested(ItemSchema)

class InventorySchema(Schema):
    user_id = fields.Int(attribute='user_id')
    char_limit = fields.Int()
    coins = fields.Int()
    hero_exp = fields.Int()

class InventoryView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        charSerializer = CharacterSchema(Character.objects.filter(user=request.user), exclude=('weapon',), many=True)
        itemSerializer = ItemSchema(Item.objects.filter(user=request.user), many=True)
        inventorySerializer = InventorySchema(Inventory.objects.get(user=request.user))
        return Response({'characters':charSerializer.data, 'items':itemSerializer.data, 'details':inventorySerializer.data})

class BaseInfoView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        charSerializer = BaseCharacterSchema(BaseCharacter.objects.all(), many=True)
        itemSerializer = BaseItemSchema(BaseItem.objects.all(), many=True)
        return Response({'characters':charSerializer.data, 'items':itemSerializer.data})

def GetTotalExp(level):
    return math.floor((level-1)*50 + ((level-1)**3.6)/10)

class TryLevelView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        
        serializer = LevelUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_char_id = serializer.validated_data['target_char_id']
        
        curChar = Character.objects.get(char_id=target_char_id)
        level = curChar.level
        curExp = GetTotalExp(level)
        nextExp = GetTotalExp(level+1)
        deltaExp = nextExp-curExp

        inventory = request.user.inventory
        
        if deltaExp > inventory.coins:
            return Response({'status': False})

        inventory.coins -= deltaExp
        curChar.level += 1

        inventory.save()
        curChar.save()

        return Response({'status':True})



