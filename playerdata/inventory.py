import math
from enum import Enum
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import constants, server, base, level_booster
from playerdata.models import Character, UserInfo, ServerStatus
from playerdata.models import Item
from . import formulas
from .questupdater import QuestUpdater
from .serializers import EquipItemSerializer, UnequipItemSerializer, ValueSerializer, ScrapItemSerializer
from .serializers import TargetCharSerializer


class ItemSchema(Schema):
    item_id = fields.Int()
    user_id = fields.Int(attribute='user_id')
    item_type = fields.Int(attribute='item_type_id')
    exp = fields.Int()
    stars = fields.Method('get_star_level')

    def get_star_level(self, item):
        return exp_to_stars(item.exp, item.item_type.rarity)


class CharacterSchema(Schema):
    char_id = fields.Int()
    user_id = fields.Int(attribute='user_id')
    char_type = fields.Int(attribute='char_type_id')
    level = fields.Method('get_char_level')
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

    def get_char_level(self, char):
        if base.is_flag_active(base.FlagName.LEVEL_MATCH):
            if char.is_boosted:
                if char.char_id in char.user.levelbooster.top_five and not char.user.levelbooster.is_enhanced:
                    return char.level

                return char.user.levelbooster.booster_level

            return char.level

        # TODO: remove after 1.1.3
        if char.level == constants.MAX_CHARACTER_LEVEL:
            return char.user.levelbooster.booster_level
        else:
            return char.level


class ChestSchema(Schema):
    id = fields.Int()
    rarity = fields.Int()
    locked_until = fields.DateTime()
    tier_rank = fields.Int()


class InventorySchema(Schema):
    user_id = fields.Int(attribute='user_id')
    char_limit = fields.Int()
    coins = fields.Int()
    gems = fields.Int()
    dust = fields.Int()
    relic_stones = fields.Int()
    hero_exp = fields.Int()
    pet_points = fields.Int()
    rare_shards = fields.Int()
    epic_shards = fields.Int()
    legendary_shards = fields.Int()
    ember = fields.Int()
    active_pet_id = fields.Int()
    gems_bought = fields.Int()
    dust_fast_reward_hours = fields.Int()
    coins_fast_reward_hours = fields.Int()

    chest_slot_1 = fields.Nested(ChestSchema)
    chest_slot_2 = fields.Nested(ChestSchema)
    chest_slot_3 = fields.Nested(ChestSchema)
    chest_slot_4 = fields.Nested(ChestSchema)
    login_chest = fields.Nested(ChestSchema)

    # TODO: delete this on 0.1.2
    player_level = fields.Method("get_player_lvl")
    player_exp = fields.Method("get_player_exp")

    pets_unlocked = fields.List(fields.Int())
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
        level_booster.try_eval_save_top_five(request.user)  # evaling here guarantees correctness and is lazier than evaling at each levelup/refunds

        char_serializer = CharacterSchema(Character.objects.filter(user=request.user), many=True)
        item_serializer = ItemSchema(Item.objects.filter(user=request.user), many=True)
        inventory_serializer = InventorySchema(request.user.inventory)
        return Response(
                {'status': True, 'characters': char_serializer.data, 'items': item_serializer.data, 'details': inventory_serializer.data})


class InventoryHeaderView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        inventory_serializer = InventorySchema(request.user.inventory)
        if server.is_server_version_higher('0.5.0'):
            return Response({'status': True, 'inventory_details': inventory_serializer.data})
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
            return Response({'status': False, 'reason': 'character has already hit max level ' + str(
                constants.MAX_CHARACTER_LEVEL) + '!'})
        if base.is_flag_active(base.FlagName.LEVEL_MATCH) and target_character.is_boosted:
            return Response({'status': False, 'reason': 'character is being boosted on the Power Bound!'})

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

        PRESTIGE_CAP = constants.PRESTIGE_CAP_BY_RARITY_15[target_character.char_type.rarity]

        if target_character.prestige >= PRESTIGE_CAP:
            return Response({'status': False, 'reason': 'character has already hit max prestige!'})

        copies_required = formulas.next_prestige_copies(target_character.prestige, target_character.char_type.rarity)

        if target_character.copies < copies_required:
            return Response({'status': False, 'reason': 'not enough copies to prestige!'})

        target_character.copies -= copies_required
        target_character.prestige += 1
        target_character.save()

        QuestUpdater.add_progress_by_type(request.user, constants.ASCEND_X_HEROES, 1)

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

        if target_character.is_boosted:
            return Response({'status': False, 'reason': 'can not refund a boosted level character!'})

        if request.user.levelbooster.is_enhanced and target_character in request.user.levelbooster.top_five:
            return Response({'status': False, 'reason': 'can not refund an elite five character!'})

        inventory = request.user.inventory
        cost = constants.REFUND_CHAR_GEMS if server.is_server_version_higher('1.1.0') else target_character.level * constants.REFUND_GEMS_COST_PER_LVL
        if inventory.gems < cost:
            return Response({'status': False, 'reason': 'not enough gems!'})

        inventory.gems -= cost
        refund = refund_char_resources(inventory, target_character.level)

        target_character.level = 1

        # Unequip all items, a bit more efficient than looping unequip_item_from_char since it has a save() each time
        target_character.hat = None
        target_character.armor = None
        target_character.boots = None
        target_character.weapon = None
        target_character.trinket_1 = None
        target_character.trinket_2 = None

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


# TODO(0.5.0): Can be removed after
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

        # TODO(0.5.0): Remove
        if char.level < ITEM_RARITY_MIN_LEVEL[item.item_type.rarity] and not server.is_server_version_higher('0.5.0'):
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
        QuestUpdater.add_progress_by_type(request.user, constants.EQUIP_GEAR, 1)
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


# TODO: Tune numbers
def get_item_rarity_base_expvalue(rarity):
    if rarity == 0:
        base = 10
    elif rarity == 1:
        base = 20
    elif rarity == 2:
        base = 200
    elif rarity == 3:
        base = 2000
    else:
        raise Exception("invalid item rarity: " + str(rarity))

    return base


def calculate_item_exp(item):
    base = get_item_rarity_base_expvalue(item.item_type.rarity)
    return base + item.exp


MAX_ITEM_STAR = 5


# TODO: Tune numbers
def exp_to_stars(exp, rarity):
    base = get_item_rarity_base_expvalue(rarity)

    if exp < base:
        return 0
    elif exp < base * 3:
        return 1
    elif exp < base * 7:
        return 2
    elif exp < base * 15:
        return 3
    elif exp < base * 31:
        return 4
    elif exp < base * 63:
        return 5
    elif exp < base * 111:
        return 6
    elif exp < base * 175:
        return 7
    elif exp < base * 303:
        return 8
    elif exp < base * 495:
        return 9
    else:
        return 10


def scrap_items(scraps, target_item):
    total_exp = sum(calculate_item_exp(item) for item in scraps)

    scraps.delete()
    target_item.exp += total_exp
    target_item.save()
    return target_item, total_exp


class ScrapItemsView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ScrapItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        scrap_item_ids = serializer.validated_data['scrap_item_ids']
        target_item_id = serializer.validated_data['target_item_id']

        if target_item_id in scrap_item_ids:
            return Response({'status': False, 'reason': 'target item cannot be in the scrapped items'})

        scraps = Item.objects.filter(item_id__in=scrap_item_ids, user=request.user)
        if scraps.first() is None:
            return Response({'status': False, 'reason': 'invalid item ids'})

        target_item = Item.objects.filter(item_id=target_item_id, user=request.user).first()
        if target_item is None:
            return Response({'status': False, 'reason': 'user does not own the item'})

        if target_item.item_type.rarity < 1:
            return Response({'status': False, 'reason': 'cannot enhance Common items'})

        if exp_to_stars(target_item.exp, target_item.item_type.rarity) == MAX_ITEM_STAR:
            return Response({'status': False, 'reason': 'max star level reached'})

        target_item, exp_upgraded = scrap_items(scraps, target_item)

        QuestUpdater.add_progress_by_type(request.user, constants.UPGRADE_ITEM, 1)
        QuestUpdater.add_progress_by_type(request.user, constants.UPGRADE_ITEM_POINTS, exp_upgraded)

        target_item_schema = ItemSchema(target_item)
        return Response({'status': True, 'target_item': target_item_schema.data})
