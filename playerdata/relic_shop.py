import random
from datetime import date, datetime, timedelta
from functools import lru_cache

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata import base, rolls
from playerdata.models import BaseCharacter, RelicShop
from .serializers import IntSerializer

EPIC_COST = 600
RARE_COST = 160


class BuyRelicView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        char_type = serializer.validated_data['value']

        seed_int = get_relic_seed_int()
        if char_type not in get_relics(seed_int):
            return Response({'status': False, 'reason': 'this hero is not currently for sale!'})

        inventory = request.user.inventory
        relic_cost = get_relic_cost(char_type)

        if relic_cost > inventory.relic_stones:
            return Response({'status': False, 'reason': 'not enough relic stones!'})

        if char_type in request.user.relicshop.purchased_relics:
            return Response({'status': False, 'reason': 'already purchased this relic!'})

        inventory.relic_stones -= relic_cost
        inventory.save()

        request.user.relicshop.purchased_relics.append(char_type)
        request.user.relicshop.save()

        rolls.insert_character(request.user, char_type)

        return Response({'status': True})


def get_relic_cost(char_type: int):
    rarity = base.get_char_rarity(char_type)
    if rarity == 3:
        return EPIC_COST
    else:
        return RARE_COST


# Isolate for better mocking
def get_relic_seed_int():
    return date.today().month + (date.today().day // 16)


# Returns a list of basechar id's that are available for purchase (bimonthly)
@lru_cache()
def get_relics(seed_int=1):
    # random seed to the half month
    # rng = random.Random(seed_int)

    rares = list(BaseCharacter.objects.filter(rarity=2, rollable=True).values_list('char_type', flat=True))
    epics = list(BaseCharacter.objects.filter(rarity=3, rollable=True).values_list('char_type', flat=True))

    # rare_chars = rng.sample(rares, 3)
    # epic_chars = rng.sample(epics, 3)

    return epics + rares


# The hour is 4am UTC or 12am EST during non-daylight savings
def get_relic_reset_date():
    today = datetime.today()
    if today.day >= 16:
        return (datetime(today.year, today.month, 1, 4) + timedelta(days=32)).replace(day=1)
    else:
        return datetime(today.year, today.month, 16, 4)


# Cron job on 1st and 16th day of the month
def refresh_shop():
    relics_shops = RelicShop.objects.all()
    for relic in relics_shops:
        relic.purchased_relics = []

    RelicShop.objects.bulk_update(relics_shops, ['purchased_relics'])


class GetRelicShopView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        seed_int = get_relic_seed_int()
        purchased_relics = request.user.relicshop.purchased_relics

        return Response({
            'status': True,
            'relics': get_relics(seed_int),
            'purchased_relics': purchased_relics,
            'next_reset': get_relic_reset_date()
        })
