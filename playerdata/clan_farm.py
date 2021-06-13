"""Clan farms.

Design doc:
https://docs.google.com/document/d/1Dxsy1OfBRzbHIEXHfrZZf45SjSatXJ8RTqZ81W5NKdw/edit
"""

import datetime
import enum
import math

from django.db import transaction
from django.db.models import Prefetch
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Clan2, ClanMember, ClanFarming


def current_week():
    today = datetime.date.today()
    return today - datetime.timedelta(days=today.weekday())


def last_week():
    return current_week() - datetime.timedelta(days=7)


def refresh_farm_status(status):
    if status.previous_farm_reward < last_week():
        status.previous_farm_reward = last_week()
        status.unclaimed_rewards = {
            'total_farms': sum(len(f) for f in status.daily_farms),
            # NOTE: user ID is implicitly casted to string as JSONs only hold
            # strings, so we should cast it back.
            'clan_members': list({int(uid) for f in status.daily_farms for uid in f}),
        }
        status.reset()
        status.save()
        

class ClanFarmingStatus(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def get(self, request):
        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of a clan!'})

        status, _ = ClanFarming.objects.get_or_create(clan=clan)
        refresh_farm_status(status)
        
        weekday = datetime.datetime.today().date().weekday()
        farmed_today = request.user.id in status.daily_farms[weekday]
        total_farms = sum(len(f) for f in status.daily_farms)
        if request.user.id in status.unclaimed_rewards['clan_members']:
            unclaimed_rewards = status.unclaimed_rewards['total_farms']
            status.unclaimed_rewards['clan_members'].remove(request.user.id)
            status.save()

            # Check if users have already claimed rewards for the last week,
            # if they have force it to be 0 (NOTE: this is not visually
            # clear for now, but we can add another flag in the response if
            # we need for the UI).
            clanmember = request.user.userinfo.clanmember
            if clanmember.last_farm_reward == last_week():
                unclaimed_rewards = 0
            else:
                clanmember.last_farm_reward = last_week()
                clanmember.save()
            # TODO: actually add reward to user inventory.
        else:
            unclaimed_rewards = 0

        return Response({'status': True,
                         'farmed_today': farmed_today,
                         'total_farms': total_farms,
                         'unclaimed_rewards': unclaimed_rewards})


class ClanFarmingFarm(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of a clan!'})

        status, _ = ClanFarming.objects.get_or_create(clan=clan)
        refresh_farm_status(status)

        weekday = datetime.datetime.today().date().weekday()
        if str(request.user.id) in status.daily_farms[weekday]:
            return Response({'status': False, 'reason': 'Already farmed for the day!'})
        status.daily_farms[weekday][str(request.user.id)] = True
        status.save()
        return Response({'status': True})
