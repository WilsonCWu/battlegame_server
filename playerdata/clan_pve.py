"""Clan PVE

Design doc:
https://docs.google.com/document/d/1oG73A93V7ZO6e3CWrwM1yHKWOW9lGHGCxuyuJiwgjMs/edit.
"""

import datetime
import enum

from django.db import transaction
from django.db.models import Prefetch
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from .models import ClanPVEResult, ClanPVEStatus, ClanPVEEvent, Clan2, ClanMember


class ClanPVEBoss(enum.Enum):
    TheWall = '1'
    OneShotWonder = '2'
    AOEBoss = '3'


class ClanPVESerializer(serializers.Serializer):
    boss_type = serializers.ChoiceField(list((opt.value, opt.name) for opt in ClanPVEBoss))
    score = serializers.IntegerField()


# TODO: APIs for character lending.
 
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


class ClanPVEStartView(APIView):
    """Attempt to start a Clan PVE game."""
    permission_classes = (IsAuthenticated,)

    def start_event(user, boss_type):
        """Returns (<can_start: boolean>, <reason, str>)."""

        # Check if the clan is elgible to start the run.
        clan = user.userinfo.clanmember.clan2
        if not clan:
            return (False, 'User not part of any clans!')
        if clan.exp < CLAN_EXP_BAR[boss_type]:
            return (False, 'Clan not high enough level!')

        # Get the clan's current event.
        event = ClanPVEEvent.objects.filter(clan=clan).order_by('-date').first()
        if not event:
            return (False, 'Clan has no event!')

        # Get the user's status.
        event_status = ClanPVEStatus.objects.filter(user=user, event=event).first()
        if not event_status:
            return (False, 'User was not enrolled in the event!')

        if datetime.datetime.today().date() == event.date:
            if event_status.tickets_1[boss_type] <= 0:
                return (False, 'Not enough tickets!')
            event_status.tickets_1[boss_type] -= 1
        elif datetime.datetime.today().date() == event.date + datetime.timedelta(days=1):
            if event_status.tickets_2[boss_type] <= 0:
                return (False, 'Not enough tickets!')
            event_status.tickets_2[boss_type] -= 1
        elif datetime.datetime.today().date() == event.date + datetime.timedelta(days=2):
            if event_status.tickets_3[boss_type] <= 0:
                return (False, 'Not enough tickets!')
            event_status.tickets_3[boss_type] -= 1
        else:
            return (False, 'Out of event time range!')

        event_status.save()
        return (True, '')

    @transaction.atomic
    def post(self, request):
        serializer = ClanPVEStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        started, reason = ClanPVEStartView.start_event(request.user, serializer.validated_data['boss_type'])
        return Response({'status': started, 'reason': reason})


class ClanPVEStartEventView(APIView):
    """Initiate a Clan event for your current clan, to be started next day."""
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of any clans!'})

        # Ensure that you have permission to start.
        if not request.user.userinfo.clanmember.is_admin:
            return Response({'status': False, 'reason': 'Need admin permissions!'})
            
        target_date = datetime.date.today() + datetime.timedelta(days=1)
        # Ensure that you don't have an event in the last 7 days.
        if ClanPVEEvent.objects.filter(clan=clan, date__gt=target_date-datetime.timedelta(days=7)).exists():
            return Response({'status': False, 'reason': 'Last event within 7 days!'})

        event = ClanPVEEvent.objects.create(clan=clan, date=target_date, started_by=request.user)

        # Generate event statuses for all current clan members.
        clan_query = Clan2.objects.filter(id=clan.id).prefetch_related(Prefetch(
            'clanmember_set', to_attr='clan_members',
            queryset=ClanMember.objects.select_related('userinfo__user')))
        clanmembers = clan_query[0].clan_members
        # Default ticket setup.
        tickets = {'1': 1, '2': 1, '3': 1}
        for member in clanmembers:
            u = member.userinfo.user
            # TODO: setup character lending.
            char_lending = {'default': True, 'characters': []}
            ClanPVEStatus.objects.create(user=u, event=event, tickets_1=tickets,
                                         tickets_2=tickets, tickets_3=tickets,
                                         character_lending=char_lending)
        return Response({'status': True, 'start_date': target_date})


class ClanPVEStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def get(self, request):
        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of any clans!'})

        event = ClanPVEEvent.objects.filter(clan=clan).order_by('-date').first()
        if event and datetime.datetime.today().date() > event.date + datetime.timedelta(days=2):
            event = None

        if not event:
            return Response({'status': True, 'has_event': False})
            
        event_status = ClanPVEStatus.objects.filter(user=request.user, event=event).first()
        if not event_status:
            return Response({'status': True, 'has_event': False})

        tickets = None
        if event:
            if datetime.datetime.today().date() == event.date:
                tickets = event_status.tickets_1
            elif datetime.datetime.today().date() == event.date + datetime.timedelta(days=1):
                tickets = event_status.tickets_2
            elif datetime.datetime.today().date() == event.date + datetime.timedelta(days=2):
                tickets = event_status.tickets_3
        return Response({'status': True, 'has_event': True,
                         'start_time': event.date, 'tickets': tickets})
