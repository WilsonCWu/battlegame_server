from django.db.transaction import atomic
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from django.utils import timezone
from datetime import datetime, timedelta

from playerdata import formulas, constants
from playerdata.models import Character
from playerdata.serializers import FillBoosterSlotSerializer, IntSerializer


class LevelBoosterSchema(Schema):
    booster_level = fields.Int()
    unlocked_slots = fields.Int()
    slots = fields.List(fields.Int())
    cooldown_slots = fields.List(fields.DateTime())
    pentagram = fields.Method("get_schema_pentagram_chars")

    def get_schema_pentagram_chars(self, level_booster):
        return get_pentagram_chars_id_list(level_booster.user)


# Gets the top 5 non-boosted chars by level
def get_pentagram_chars(user):
    return Character.objects.filter(user=user, is_boosted=False).order_by('-level')[:5]


def get_pentagram_chars_id_list(user):
    return list(get_pentagram_chars(user).values_list('char_id', flat=True))


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

        if request.user.levelbooster.slots[slot_id] != -1:
            return Response({'status': False, 'reason': 'slot is currently occupied'})

        if char_id in request.user.levelbooster.slots:
            return Response({'status': False, 'reason': 'hero is already being used'})

        if char_id in get_pentagram_chars_id_list(request.user):
            return Response({'status': False, 'reason': 'cannot use a hero on the pentagram'})

        char = Character.objects.filter(user=request.user, char_id=char_id).first()
        if char is None:
            return Response({'status': False, 'reason': 'invalid char_id'})

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

        gem_cost = formulas.unlock_level_booster_slot_cost(request.user.levelbooster.unlocked_slots + 1)

        if request.user.inventory.gems < gem_cost:
            return Response({'status': False, 'reason': 'not enough gems to unlock slot'})

        request.user.inventory.gems -= gem_cost
        request.user.inventory.save()

        request.user.levelbooster.unlocked_slots += 1
        request.user.levelbooster.save()

        return Response({'status': True, 'unlocked_slots': request.user.levelbooster.unlocked_slots})
