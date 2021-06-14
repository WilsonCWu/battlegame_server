import random
from datetime import date, datetime, timedelta
from functools import lru_cache

from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from playerdata import base, rolls
from playerdata.models import BaseCharacter, RelicShop
from .serializers import SlotSerializer


NUM_SLOTS_PER_RARITY = [0, 0, 2, 2, 1]


class SetWishlistSlotView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = SlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        slot_id = serializer.validated_data['slot_id']
        char_type = serializer.validated_data['char_id']  # In this case it's char_type not char_id

        rarity = base.get_char_rarity(char_type)

        if slot_id < 0 or slot_id >= NUM_SLOTS_PER_RARITY[rarity]:
            return Response({'status': False, 'reason': 'invalid slot_id'})

        if rarity == 2:
            wishlist = request.user.wishlist.rares
        elif rarity == 3:
            wishlist = request.user.wishlist.epics
        elif rarity == 4:
            wishlist = request.user.wishlist.legendaries
        else:
            return Response({'status': False, 'reason': 'invalid char_type rarity'})

        if char_type in wishlist:
            return Response({'status': False, 'reason': 'char already in wishlist'})

        wishlist[slot_id] = char_type
        wishlist.save()

        return Response({'status': True})
