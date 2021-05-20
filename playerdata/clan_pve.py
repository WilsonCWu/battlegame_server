"""Clan PVE

Design doc:
https://docs.google.com/document/d/1oG73A93V7ZO6e3CWrwM1yHKWOW9lGHGCxuyuJiwgjMs/edit.
"""

import datetime
import enum

from django.db import transaction
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from .models import ClanPVEResult, ClanPVEStatus, Clan2


class ClanPVEBoss(enum.Enum):
    TheWall = '1'
    OneShotWonder = '2'
    AOEBoss = '3'


class ClanPVESerializer(serializers.Serializer):
    boss_type = serializers.ChoiceField(list((opt.value, opt.name) for opt in ClanPVEBoss))
    score = serializers.IntegerField()


# TODO: APIs for character lending.
# TODO: APIs for displaying PVE status.
# TODO: crons for lock in.
 
class ClanPVEResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def calculate_rewards(self):
        pass

    def calculate_exp(self):
        # We expect a clan to make 20 runs to level two, and an additional 60
        # runs to level three. As a result, let's just leave this as one and
        # calculate the level as such.
        return 1

    @transaction.atomic
    def post(self, request):
        serializer = ClanPVESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        boss_type = serializer.validated_data['boss_type']
        # Update the best score for the user if applicable.
        result, _ = ClanPVEResult.objects.get_or_create(
            user=request.user,
            boss=boss_type,
        )
        result.best_score = max(result.best_score, serializer.validated_data['score'])
        result.save()

        # TODO: give user rewards.
        rewards = self.calculate_rewards()

        # Give clan experience per run.
        exp = self.calculate_exp()
        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of any clans!'})
 
        clan.exp += exp
        clan.save()

        return Response({'status': True})


CLAN_EXP_BAR = {
    '1': 0,
    '2': 20,
    '3': 80,
}


class ClanPVEStartSerializer(serializers.Serializer):
    boss_type = serializers.ChoiceField(list((opt.value, opt.name) for opt in ClanPVEBoss))


def get_date():
    """Isolate this function so it can be easily mocked."""
    return datetime.datetime.today().weekday()


class ClanPVEStartView(APIView):
    """Attempt to start a Clan PVE game."""
    permission_classes = (IsAuthenticated,)


    def pve_status(user):
        day = get_date()
        day_to_str = {4: 'Fri', 5: 'Sat', 6: 'Sun'}
        if day not in day_to_str:
            return None
        return ClanPVEStatus.objects.get(user=user, day=day_to_str[day])

    def can_start(user, boss_type):
        """Returns (<can_start: boolean>, <reason, str>)."""

        # Check if the clan is elgible to start the run.
        clan = user.userinfo.clanmember.clan2
        if not clan:
            return (False, 'User not part of any clans!')
        if clan.exp < CLAN_EXP_BAR[boss_type]:
            return (False, 'Clan not high enough level!')
        
        # Check if the user still have tickets.
        pve_status = ClanPVEStartView.pve_status(user)
        if not pve_status:
            return (False, 'Not Fri, Sat, or Sunday!')
        if pve_status.tickets[boss_type] <= 0:
            return (False, 'Not enough tickets!')

        return (True, '')

    @transaction.atomic
    def post(self, request):
        serializer = ClanPVEStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        can_start, reason = ClanPVEStartView.can_start(request.user, serializer.validated_data['boss_type'])
        if not can_start:
            return Response({'status': False, 'reason': reason})

        # Decrement the ticket.
        pve_status = ClanPVEStartView.pve_status(request.user)
        pve_status.tickets[serializer.validated_data['boss_type']] -= 1
        pve_status.save()

        return Response({'status': True})

