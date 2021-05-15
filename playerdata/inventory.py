from enum import Enum
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import constants
from playerdata.models import Character, UserInfo, ServerStatus
from playerdata.models import Item
from . import formulas
from .questupdater import QuestUpdater
from .serializers import EquipItemSerializer, UnequipItemSerializer, ValueSerializer
from .serializers import TargetCharSerializer


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
    is_boosted = fields.Bool()

    hat = fields.Nested(ItemSchema)
    armor = fields.Nested(ItemSchema)
    weapon = fields.Nested(ItemSchema)
    boots = fields.Nested(ItemSchema)
    trinket_1 = fields.Nested(ItemSchema)
    trinket_2 = fields.Nested(ItemSchema)


class ChestSchema(Schema):
    id = fields.Int()
    rarity = fields.Int()
    locked_until = fields.DateTime()


class InventorySchema(Schema):
    user_id = fields.Int(attribute='user_id')
    char_limit = fields.Int()
    coins = fields.Int()
    gems = fields.Int()
    dust = fields.Int()
    hero_exp = fields.Int()

    chest_slot_1 = fields.Nested(ChestSchema)
    chest_slot_2 = fields.Nested(ChestSchema)
    chest_slot_3 = fields.Nested(ChestSchema)
    chest_slot_4 = fields.Nested(ChestSchema)
    #TODO: delete this on 0.1.2
    player_level = fields.Method("get_player_lvl")
    player_exp = fields.Method("get_player_exp")

    profile_pics = fields.List(fields.Int())

    daily_dungeon_ticket = fields.Int()
    daily_dungeon_golden_ticket = fields.Int()

    def get_player_lvl(self, inventory):
        userinfo = UserInfo.objects.get(user_id=inventory.user_id)
        return formulas.exp_to_level(userinfo.player_exp)

    def get_player_exp(self, inventory):
        userinfo = UserInfo.objects.get(user_id=inventory.user_id)
        return userinfo.player_exp

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
        serializer = TargetCharSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_char_id = serializer.validated_data['target_char_id']
        target_character = Character.objects.get(char_id=target_char_id)
        if target_character.user != request.user:
            return Response({'status': False, 'reason': 'character does not belong to user!'})
        if target_character.level >= constants.MAX_CHARACTER_LEVEL:
            return Response({'status': False, 'reason': 'character has already hit max level ' + str(constants.MAX_CHARACTER_LEVEL) + '!'})

        cur_coins = formulas.char_level_to_coins(target_character.level)
        next_coins = formulas.char_level_to_coins(target_character.level + 1)
        delta_coins = next_coins - cur_coins

        inventory = request.user.inventory
        if delta_coins > inventory.coins:
            return Response({'status': False, 'reason': 'not enough coins!'})

        cur_dust = formulas.char_level_to_dust(target_character.level)
        next_dust = formulas.char_level_to_dust(target_character.level + 1)
        delta_dust = next_dust - cur_dust

        if delta_dust > inventory.dust:
            return Response({'status': False, 'reason': 'not enough dust!'})

        inventory.dust -= delta_dust

        inventory.coins -= delta_coins
        target_character.level += 1

        inventory.save()
        target_character.save()

        QuestUpdater.add_progress_by_type(request.user, constants.LEVEL_UP_A_HERO, 1)

        return Response({'status': True})


class TryPrestigeView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = TargetCharSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        target_char_id = serializer.validated_data['target_char_id']
        target_character = Character.objects.get(char_id=target_char_id)
        if target_character.user != request.user:
            return Response({'status': False, 'reason': 'character does not belong to user!'})
        if target_character.prestige >= constants.PRESTIGE_CAP_BY_RARITY[target_character.char_type.rarity]:
            return Response({'status': False, 'reason': 'character has already hit max prestige!'})

        copies_required = formulas.next_prestige_copies(target_character.prestige)

        if target_character.copies < copies_required:
            return Response({'status': False, 'reason': 'not enough copies to prestige!'})

        target_character.copies -= copies_required
        target_character.prestige += 1
        target_character.save()

        return Response({'status': True})


# retired_copies should only be passed in if retiring
def refund_char_resources(inventory, level, retired_copies=0):
    refunded_coins = formulas.char_level_to_coins(level)
    refunded_dust = formulas.char_level_to_dust(level) + formulas.char_level_to_dust(1) * max(0, (retired_copies - 1))
    essence_collected = constants.ESSENCE_PER_COMMON_CHAR_RETIRE * retired_copies

    inventory.coins += refunded_coins
    inventory.dust += refunded_dust
    inventory.essence += essence_collected
    inventory.save()

    return {'refunded_coins': refunded_coins, 'refunded_dust': refunded_dust, 'essence': essence_collected}


class RefundCharacter(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_char_id = serializer.validated_data['value']
        target_character = Character.objects.get(char_id=target_char_id)

        if target_character.user != request.user:
            return Response({'status': False, 'reason': 'character does not belong to user!'})

        if target_character.level < 2:
            return Response({'status': False, 'reason': 'can only refund character over level 1!'})

        inventory = request.user.inventory
        if inventory.gems < constants.DUSTING_GEMS_COST:
            return Response({'status': False, 'reason': 'not enough gems!'})

        inventory.gems -= constants.DUSTING_GEMS_COST
        refund = refund_char_resources(inventory, target_character.level)

        target_character.level = 1
        inventory.save()
        target_character.save()

        return Response({'status': True, 'coins': refund["refunded_coins"], 'dust': refund["refunded_dust"]})


class RetireCharacter(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_char_id = serializer.validated_data['value']
        target_character = Character.objects.get(char_id=target_char_id)

        if target_character.user != request.user:
            return Response({'status': False, 'reason': 'character does not belong to user!'})

        if target_character.char_type.rarity != 1:
            return Response({'status': False, 'reason': 'can only retire common rarity heroes!'})

        inventory = request.user.inventory
        refund = refund_char_resources(inventory, target_character.level, target_character.copies)

        target_character.delete()
        inventory.save()

        return Response({'status': True, 'essence': refund["essence"],
                         'coins': refund["refunded_coins"], 'dust': refund["refunded_dust"]})


class SetAutoRetire(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_auto_retire = serializer.validated_data['value']

        request.user.inventory.is_auto_retire = is_auto_retire
        request.user.inventory.save()

        return Response({'status': True})


class SlotType(Enum):
    HAT = 'H'
    ARMOR = 'A'
    BOOTS = 'B'
    WEAPON = 'W'
    TRINKET_1 = 'T1'
    TRINKET_2 = 'T2'

# returns id of char item is unequipped from, and its slot
# assumes slot is valid, and item belongs to user
# for trinkets, will unequip from both
# assumes T1/T2 for trinkets, not T
def unequip_item(item, target_slot):
    char = None
    # TODO: hasattr is pretty gross, but catching exception method is worse, espec with trinkets
    if target_slot == SlotType.HAT.value:
        if hasattr(item, 'hat'):
            char = item.hat
    elif target_slot == SlotType.ARMOR.value:
        if hasattr(item, 'armor'):
            char = item.armor
    elif target_slot == SlotType.BOOTS.value:
        if hasattr(item, 'boots'):
            char = item.boots
    elif target_slot == SlotType.WEAPON.value:
        if hasattr(item, 'weapon'):
            char = item.weapon
    elif target_slot == SlotType.TRINKET_1.value or target_slot == SlotType.TRINKET_2.value:
        # assuming trinket is in valid state, and not doubly equipped
        if hasattr(item, 'trinket_1'):
            char = item.trinket_1
            target_slot = SlotType.TRINKET_1.value
        if hasattr(item, 'trinket_2'):
            if char:
                Exception("item already equipped in 2 trinket spots: " + str(item.item_id))
            char = item.trinket_2
            target_slot = SlotType.TRINKET_2.value
    else:
        raise Exception("invalid target_slot " + target_slot)
    
    if char:
        unequip_item_from_char(char, target_slot)
        return char.char_id, target_slot
    else:
        return -1, ""

def unequip_item_from_char(char, slot):
    if slot == SlotType.HAT.value:
        char.hat = None
    elif slot == SlotType.ARMOR.value:
        char.armor = None
    elif slot == SlotType.BOOTS.value:
        char.boots = None
    elif slot == SlotType.WEAPON.value:
        char.weapon = None
    elif slot == SlotType.TRINKET_1.value:
        char.trinket_1 = None
    elif slot == SlotType.TRINKET_2.value:
        char.trinket_2 = None

    char.save()


ITEM_RARITY_MIN_LEVEL = {
    0: 20,
    1: 80,
    2: 140,
    3: 200,
}
    
class EquipItemView(APIView):
    permission_classes = (IsAuthenticated,)

    # Note that this also unequips the item if already equipped.
    @transaction.atomic
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

        if char.level < ITEM_RARITY_MIN_LEVEL[item.item_type.rarity]:
            return Response({'status': False, 'reason': 'character not high enough level to equip item'})

        # Unequip item if already equipped.
        unequip_char_id, unequip_slot = unequip_item(item, target_slot)
        if unequip_char_id == char.char_id:
            char.refresh_from_db()

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
        except Exception as e:
            return Response({'status': False, 'reason': str(e)})

        char.save()
        return Response({'status': True, 'unequip_char_id': unequip_char_id, 'unequip_slot': unequip_slot})

class UnequipItemView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = UnequipItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_char_id = serializer.validated_data['target_char_id']
        target_slot = serializer.validated_data['target_slot']

        char = Character.objects.get(char_id=target_char_id)

        if char.user != request.user:
            return Response({'status': False, 'reason': 'user does not own the character'})

        unequip_item_from_char(char, target_slot)
        return Response({'status': True})
