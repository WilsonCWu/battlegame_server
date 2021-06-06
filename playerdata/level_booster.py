from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from django.utils import timezone
from datetime import datetime, timedelta

from playerdata import formulas, constants
from playerdata.models import Character
from playerdata.questupdater import QuestUpdater
from playerdata.serializers import FillBoosterSlotSerializer, IntSerializer

MIN_NUM_OF_MAXED_CHARS = 1


class LevelBoosterSchema(Schema):
    booster_level = fields.Int()
    unlocked_slots = fields.Int()
    slots = fields.List(fields.Int())
    cooldown_slots = fields.List(fields.DateTime())
    is_available = fields.Method("get_is_available")

    def get_is_available(self, level_booster):
        return get_max_out_char_count(level_booster.user) >= MIN_NUM_OF_MAXED_CHARS


# Get all 240 chars that are 10 star
def get_max_out_char_count(user):
    chars = Character.objects.filter(user=user, level=240)
    count = 0
    for char in chars:
        if char.prestige == constants.PRESTIGE_CAP_BY_RARITY[char.char_type.rarity]:
            count += 1

    return count


# max cap is raised by 5 per maxed out hero
def get_level_cap(user):
    return constants.MAX_CHARACTER_LEVEL + get_max_out_char_count(user) * 5


class LevelBoosterView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        levelbooster = request.user.levelbooster
        return Response({'status': True, 'level_booster': LevelBoosterSchema(levelbooster).data})


# Fill an empty slot with an unused hero
class FillSlotView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = FillBoosterSlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data['slot_id']
        char_id = serializer.validated_data['char_id']

        if get_max_out_char_count(request.user) < MIN_NUM_OF_MAXED_CHARS:
            return Response({'status': False, 'reason': 'not enough chars to level boost!'})

        if char_id in request.user.levelbooster.slots:
            return Response({'status': False, 'reason': 'hero is already being used'})

        char = Character.objects.filter(user=request.user, char_id=char_id).first()
        if char is None:
            return Response({'status': False, 'reason': 'invalid char_id'})

        if char.level != constants.MAX_CHARACTER_LEVEL or char.prestige != constants.PRESTIGE_CAP_BY_RARITY[char.char_type.rarity]:
            return Response({'status': False, 'reason': 'must max out char before you can add it to a slot'})

        curr_time = datetime.now(timezone.utc)
        if request.user.levelbooster.cooldown_slots[slot_id] is not None and request.user.levelbooster.cooldown_slots[slot_id] > curr_time:
            return Response({'status': False, 'reason': 'slot is still in cooldown'})

        request.user.levelbooster.slots[slot_id] = char_id
        request.user.levelbooster.save()

        char.is_boosted = True
        char.save()

        return Response({'status': True, 'level': request.user.levelbooster.booster_level})


# Remove a hero from a boost slot + cooldown
class RemoveSlotView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data['value']

        if request.user.levelbooster.slots[slot_id] == -1:
            return Response({'status': False, 'reason': 'slot is already empty'})

        char_id = request.user.levelbooster.slots[slot_id]
        char = Character.objects.get(user=request.user, char_id=char_id)

        char.is_boosted = False
        char.save()

        request.user.levelbooster.slots[slot_id] = -1
        request.user.levelbooster.cooldown_slots[slot_id] = timezone.now() + timedelta(hours=24)
        request.user.levelbooster.save()

        return Response({'status': True})


# Skips the cooldown by paying gems
class SkipCooldownView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data['value']

        if request.user.inventory.gems < constants.SKIP_COOLDOWN_GEMS:
            return Response({'status': False, 'reason': 'not enough gems to unlock slot'})

        request.user.inventory.gems -= constants.SKIP_COOLDOWN_GEMS
        request.user.inventory.save()

        request.user.levelbooster.cooldown_slots[slot_id] = None
        request.user.levelbooster.save()

        return Response({'status': True})


def unlock_level_booster_slot_cost(slot_num: int):
    return 1500 * (slot_num - 1) + 3000


# Unlock the next booster slot
class UnlockSlotView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        # TODO: AFK uses just another currency (Invigorating Essence)
        #  that's just dropped very infrequently as you progress
        # serializer = IntSerializer(data=request.data)
        # serializer.is_valid(raise_exception=True)
        # resource = serializer.validated_data['value']

        gem_cost = unlock_level_booster_slot_cost(request.user.levelbooster.unlocked_slots + 1)

        if request.user.inventory.gems < gem_cost:
            return Response({'status': False, 'reason': 'not enough gems to unlock slot'})

        request.user.inventory.gems -= gem_cost
        request.user.inventory.save()

        request.user.levelbooster.unlocked_slots += 1
        request.user.levelbooster.save()

        return Response({'status': True, 'unlocked_slots': request.user.levelbooster.unlocked_slots})


# Returns the cost to level up TO this level
def level_up_coins_cost(level: int):
    adjusted_level = 440 + (level - 240) * 20
    return formulas.char_level_to_coins(adjusted_level) - formulas.char_level_to_coins(adjusted_level - 1)


# Returns the cost to level up TO this level
def level_up_dust_cost(level: int):
    return 5000 * (level - 240) + 50000


class LevelUpBooster(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        maxed_out_char_count = get_max_out_char_count(request.user)

        if maxed_out_char_count < MIN_NUM_OF_MAXED_CHARS:
            return Response({'status': False, 'reason': 'not enough chars to level boost!'})

        if request.user.levelbooster.booster_level + 1 > get_level_cap(request.user):
            return Response({'status': False, 'reason': 'level cap reached for ' + str(maxed_out_char_count) + ' maxed out heroes'})

        delta_coins = level_up_coins_cost(request.user.levelbooster.booster_level + 1)

        inventory = request.user.inventory
        if delta_coins > inventory.coins:
            return Response({'status': False, 'reason': 'not enough coins!'})

        delta_dust = level_up_dust_cost(request.user.levelbooster.booster_level + 1)

        if delta_dust > inventory.dust:
            return Response({'status': False, 'reason': 'not enough dust!'})

        inventory.dust -= delta_dust
        inventory.coins -= delta_coins
        request.user.levelbooster.booster_level += 1

        inventory.save()
        request.user.levelbooster.save()

        # This num is different from maxed_out_char_count since they aren't necessarily boosted
        num_boosted = Character.objects.filter(user=request.user, is_boosted=True).count()
        QuestUpdater.add_progress_by_type(request.user, constants.LEVEL_UP_A_HERO, num_boosted)

        return Response({'status': True})
