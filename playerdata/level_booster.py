import math

from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from django.utils import timezone
from datetime import datetime, timedelta

from playerdata import formulas, constants, base
from playerdata.models import Character, Flag
from playerdata.questupdater import QuestUpdater
from playerdata.serializers import SlotSerializer, IntSerializer

MIN_NUM_OF_MAXED_CHARS = 1


class LevelBoosterSchema(Schema):
    booster_level = fields.Int()
    unlocked_slots = fields.Int()
    slots = fields.List(fields.Int())
    cooldown_slots = fields.List(fields.DateTime())
    is_active = fields.Bool()
    is_enhanced = fields.Bool()
    top_five = fields.List(fields.Int())
    is_available = fields.Method("get_is_available")

    def get_is_available(self, level_booster):
        return is_eligible_level_boost(level_booster.user)


def is_eligible_level_boost(user):
    chars = Character.objects.filter(user=user, level=240)
    count = 0

    for char in chars:
        if is_char_eligible_level_boost(char):
            count += 1

    return count >= MIN_NUM_OF_MAXED_CHARS


def is_char_eligible_level_boost(char):
    if base.is_flag_active(base.FlagName.LEVEL_BOOST_240):
        min_stars = 6
    else:
        min_stars = 10

    return char.level == constants.MAX_CHARACTER_LEVEL and constants.PRESTIGE_TO_STAR_LEVEL(char.prestige, char.char_type.rarity) >= min_stars


# Get num of chars that are currently boosted
def get_num_boosted_chars(user):
    return Character.objects.filter(user=user, is_boosted=True).count()


# max cap is raised +1 for each prestige above 5*, capped at 10*
def get_level_cap(user):
    if base.is_flag_active(base.FlagName.LEVEL_BOOST_240):
        total_stars_past5 = 0
        chars = Character.objects.filter(user=user, level=240, is_boosted=True).select_related('char_type')

        for char in chars:
            stars_past5 = min(constants.PRESTIGE_TO_STAR_LEVEL(char.prestige, char.char_type.rarity) - 5, 5)  # capped at 5 extra levels
            total_stars_past5 += max(stars_past5, 0)
        return constants.MAX_CHARACTER_LEVEL + total_stars_past5

    return constants.MAX_CHARACTER_LEVEL + get_num_boosted_chars(user) * 5


# returns a list of ids of top 5, lowest level of the top 5
def __eval_top_five(user):
    chars = list(Character.objects.filter(user=user, is_boosted=False).order_by('-level').values('char_id', 'level')[:5])
    top_five_ids = [char["char_id"] for char in chars]
    level = chars[4]["level"]
    return top_five_ids, level


# recalculates the top five and saves it
def try_eval_save_top_five(user):
    if not base.is_flag_active(base.FlagName.LEVEL_MATCH):
        return

    if not user.levelbooster.is_active or user.levelbooster.is_enhanced:
        return

    top_five, lowest_lvl = __eval_top_five(user)
    user.levelbooster.top_five = top_five
    user.levelbooster.booster_level = lowest_lvl
    user.levelbooster.save()


def activate_levelbooster(user):
    user.levelbooster.is_active = True
    user.levelbooster.save()


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
        serializer = SlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data['slot_id']
        char_id = serializer.validated_data['char_id']

        if char_id in request.user.levelbooster.slots:
            return Response({'status': False, 'reason': 'hero is already being used'})

        char = Character.objects.filter(user=request.user, char_id=char_id).first()
        if char is None:
            return Response({'status': False, 'reason': 'invalid char_id'})

        if not base.is_flag_active(base.FlagName.LEVEL_MATCH) and not is_char_eligible_level_boost(char):
            return Response({'status': False, 'reason': 'must max out char before you can add it to a slot'})

        if base.is_flag_active(base.FlagName.LEVEL_MATCH) and char_id in request.user.levelbooster.top_five:
            return Response({'status': False, 'reason': 'hero is on the pentagram'})

        curr_time = datetime.now(timezone.utc)
        if request.user.levelbooster.cooldown_slots[slot_id] is not None and request.user.levelbooster.cooldown_slots[slot_id] > curr_time:
            return Response({'status': False, 'reason': 'slot is still in cooldown'})

        replaced_char_id = request.user.levelbooster.slots[slot_id]
        if replaced_char_id != -1:
            replaced_char = Character.objects.get(user=request.user, char_id=replaced_char_id)
            replaced_char.is_boosted = False
            replaced_char.save()

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
# https://www.desmos.com/calculator/sk1c8k11wz
def level_up_dust_cost(level: int):
    x = level - 240
    return 38000 * (1 - math.exp(-0.01 * x)) + 30*x + 20000


class LevelUpBooster(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        num_boosted_chars = get_num_boosted_chars(request.user)

        if not is_eligible_level_boost(request.user):
            return Response({'status': False, 'reason': 'not enough chars to level boost!'})

        if request.user.levelbooster.booster_level + 1 > get_level_cap(request.user):
            return Response({'status': False, 'reason': 'level cap reached for ' + str(num_boosted_chars) + ' maxed out heroes'})

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

        QuestUpdater.add_progress_by_type(request.user, constants.LEVEL_UP_A_HERO, num_boosted_chars)

        return Response({'status': True})
