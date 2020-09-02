from enum import Enum
import math

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import BaseCharacter
from playerdata.models import BaseItem
from playerdata.models import Character
from playerdata.models import Inventory
from playerdata.models import Item
from .serializers import LevelUpSerializer
from .serializers import EquipItemSerializer, UnequipItemSerializer


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
    total_damage_dealt = fields.Int()
    total_damage_taken = fields.Int()
    total_health_healed = fields.Int()
    num_games = fields.Int()
    num_wins = fields.Int()

    hat = fields.Nested(ItemSchema)
    armor = fields.Nested(ItemSchema)
    weapon = fields.Nested(ItemSchema)
    boots = fields.Nested(ItemSchema)
    trinket_1 = fields.Nested(ItemSchema)
    trinket_2 = fields.Nested(ItemSchema)


class InventorySchema(Schema):
    user_id = fields.Int(attribute='user_id')
    char_limit = fields.Int()
    coins = fields.Int()
    gems = fields.Int()
    hero_exp = fields.Int()


class InventoryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        charSerializer = CharacterSchema(Character.objects.filter(user=request.user), many=True)
        itemSerializer = ItemSchema(Item.objects.filter(user=request.user), many=True)
        inventorySerializer = InventorySchema(Inventory.objects.get(user=request.user))
        return Response(
            {'characters': charSerializer.data, 'items': itemSerializer.data, 'details': inventorySerializer.data})


def GetTotalExp(level):
    return math.floor((level - 1) * 50 + ((level - 1) ** 3.6) / 10)


class TryLevelView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = LevelUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_char_id = serializer.validated_data['target_char_id']

        curChar = Character.objects.get(char_id=target_char_id)
        level = curChar.level
        curExp = GetTotalExp(level)
        nextExp = GetTotalExp(level + 1)
        deltaExp = nextExp - curExp

        inventory = request.user.inventory

        if deltaExp > inventory.coins:
            return Response({'status': False})

        inventory.coins -= deltaExp
        curChar.level += 1

        inventory.save()
        curChar.save()

        return Response({'status': True})


class SlotType(Enum):
    HAT = 'H'
    ARMOR = 'A'
    BOOTS = 'B'
    WEAPON = 'W'
    TRINKET_1 = 'T1'
    TRINKET_2 = 'T2'


class EquipItemView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = EquipItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_char_id = serializer.validated_data['target_char_id']
        target_item_id = serializer.validated_data['target_item_id']
        target_slot = serializer.validated_data['target_slot']

        char = Character.objects.get(char_id=target_char_id)
        item = Item.objects.select_related('item_type').get(item_id=target_item_id)

        if char.user != request.user:
            return Response({'status': False, 'reason': 'user does not own the character'})

        if item.user != request.user:
            return Response({'status': False, 'reason': 'user does not own the item'})

        if item.item_type.gear_slot != target_slot[0]:
            return Response({'status': False, 'reason': 'item does not belong in the slot'})

        # Equip the item to the character.
        if target_slot == SlotType.HAT.value:
            char.hat = item
        elif target_slot == SlotType.ARMOR.value:
            char.armor = item
        elif target_slot == SlotType.BOOTS.value:
            char.boots = item
        elif target_slot == SlotType.WEAPON.value:
            char.weapon = item
        elif target_slot == SlotType.TRINKET_1.value:
            char.trinket_1 = item
        elif target_slot == SlotType.TRINKET_2.value:
            char.trinket_2 = item

        try:
            if target_slot in (SlotType.TRINKET_1.value, SlotType.TRINKET_2.value):
                # clean() validates unique trinkets across slots.
                char.clean()

            # We want to handle failures gracefully here -- especially ones
            # caused by unique key duplication from the 1-1 relationships.
            char.save()
        except Exception as e:
            return Response({'status': False, 'reason': str(e)})
        return Response({'status': True})


class UnequipItemView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = UnequipItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_char_id = serializer.validated_data['target_char_id']
        target_slot = serializer.validated_data['target_slot']

        char = Character.objects.get(char_id=target_char_id)

        if char.user != request.user:
            return Response({'status': False, 'reason': 'user does not own the character'})

        # Unequip the item to the character.
        if target_slot == SlotType.HAT.value:
            char.hat = None
        elif target_slot == SlotType.ARMOR.value:
            char.armor = None
        elif target_slot == SlotType.BOOTS.value:
            char.boots = None
        elif target_slot == SlotType.WEAPON.value:
            char.weapon = None
        elif target_slot == SlotType.TRINKET_1.value:
            char.trinket_1 = None
        elif target_slot == SlotType.TRINKET_2.value:
            char.trinket_2 = None

        char.save()
        return Response({'status': True})
