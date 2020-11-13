from enum import Enum
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import Character, UserInfo
from playerdata.models import Item
from . import formulas
from .serializers import EquipItemSerializer, UnequipItemSerializer
from .serializers import LevelUpSerializer


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
    copies = fields.Int()
    total_damage_dealt = fields.Int()
    total_damage_taken = fields.Int()
    total_health_healed = fields.Int()
    num_games = fields.Int()
    num_wins = fields.Int()

    is_tourney = fields.Bool()

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
    player_level = fields.Method("get_player_exp")

    def get_player_exp(self, inventory):
        userinfo = UserInfo.objects.get(user_id=inventory.user_id)
        return formulas.exp_to_level(userinfo.player_exp)


class InventoryView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        char_serializer = CharacterSchema(Character.objects.filter(user=request.user), many=True)
        item_serializer = ItemSchema(Item.objects.filter(user=request.user), many=True)
        inventory_serializer = InventorySchema(request.user.inventory)
        return Response(
            {'characters': char_serializer.data, 'items': item_serializer.data, 'details': inventory_serializer.data})


class InventoryHeaderView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        inventory_serializer = InventorySchema(request.user.inventory)
        return Response(inventory_serializer.data)


class TryLevelView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = LevelUpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_char_id = serializer.validated_data['target_char_id']
        target_character = Character.objects.get(char_id=target_char_id)
        if target_character.user != request.user:
            return Response({'status': False, 'reason': 'character does not belong to user!'})

        # We can only level up to the (number of copies owned * 30) + 50.
        if target_character.level + 1 > target_character.copies * 30 + 50:
            return Response({
                'status': False,
                'reason': 'level cap exceeded given %d copies!' % target_character.copies,
            })

        cur_exp = formulas.char_level_to_exp(target_character.level)
        next_exp = formulas.char_level_to_exp(target_character.level + 1)
        delta_exp = next_exp - cur_exp

        inventory = request.user.inventory
        if delta_exp > inventory.coins:
            return Response({'status': False, 'reason': 'not enough coins!'})

        inventory.coins -= delta_exp
        target_character.level += 1

        inventory.save()
        target_character.save()

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
