"""Clan PVE

Design doc:
https://docs.google.com/document/d/1oG73A93V7ZO6e3CWrwM1yHKWOW9lGHGCxuyuJiwgjMs/edit.
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
from rest_marshmallow import Schema, fields

from . import chests
from .models import Character, ClanPVEResult, ClanPVEStatus, ClanPVEEvent, Clan2, ClanMember
from .matcher import LightUserInfoSchema
from .inventory import CharacterSchema


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

    def calculate_rewards(self, score, boss_type):
        relic_stones = 0
        rewards = []

        # TODO: Tuning for each boss and damage amounts
        if boss_type == ClanPVEBoss.TheWall.value:
            relic_stones = math.log(score) * 10
        elif boss_type == ClanPVEBoss.OneShotWonder.value:
            relic_stones = math.log(score) * 10
        else:
            relic_stones = math.log(score) * 10

        relic_stones = max(140, relic_stones)

        rewards.append(chests.ChestReward(reward_type='relic_stone', value=relic_stones))
        return rewards

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
        score = serializer.validated_data['score']

        # Update the best score for the user if applicable.
        result, _ = ClanPVEResult.objects.get_or_create(
            user=request.user,
            boss=boss_type,
        )

        result.best_score = max(result.best_score, score)
        result.save()

        rewards = self.calculate_rewards(score, boss_type)
        chests.award_chest_rewards(request.user, rewards)
        reward_schema = chests.ChestRewardSchema(rewards, many=True)

        # Give clan experience per run.
        exp = self.calculate_exp()
        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of any clans!'})
 
        clan.exp += exp
        clan.save()

        # Undo PVE status.
        event = get_active_event(clan)
        if not event:
            return Response({'status': False, 'reason': 'No active event!'})
        pve_status = ClanPVEStatus.objects.filter(user=request.user, event=event).first()
        if not pve_status:
            return Response({'status': False, 'reason': 'User not enrolled in event!'})
        if pve_status.current_boss != int(boss_type):
            return Response({'status': False, 'reason': 'User started event for different boss type!'})
        pve_status.current_boss = -1
        pve_status.current_borrowed_character = -1
        pve_status.save()

        return Response({'status': True, 'rewards': reward_schema.data})


CLAN_EXP_BAR = {
    '1': 0,
    '2': 20,
    '3': 80,
}


class ClanPVEStartSerializer(serializers.Serializer):
    boss_type = serializers.ChoiceField(list((opt.value, opt.name) for opt in ClanPVEBoss))
    borrowed_character = serializers.IntegerField()


class ClanPVEStartView(APIView):
    """Attempt to start a Clan PVE game."""
    permission_classes = (IsAuthenticated,)

    def start_event(user, boss_type, borrowed_character):
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

        if event_status.current_boss != -1:
            return (False, 'User current in an existing run!')
        event_status.current_boss = int(boss_type)

        # Check if the character to be borrowed is valid.
        target_char = Character.objects.filter(char_id=borrowed_character).first()
        if not target_char:
            return (False, 'Target character does not exist.')
        # Allocate the borrowed character.
        target_status = ClanPVEStatus.objects.filter(user=target_char.user, event=event).first()
        if not target_status:
            return (False, 'Target lender not in event!')
        found = False
        for c in target_status.character_lending['characters']:
            if c['char_id'] == borrowed_character:
                if c['uses_remaining'] <= 0:
                    return (False, 'Target character out of uses!')
                c['uses_remaining'] -= 1
                found = True
        
        if not found:
            return (False, 'Target lender did not put up the character for lending!')

        event_status.current_borrowed_character = borrowed_character

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
        target_status.save()
        return (True, '')

    @transaction.atomic
    def post(self, request):
        serializer = ClanPVEStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        started, reason = ClanPVEStartView.start_event(request.user,
                                                       serializer.validated_data['boss_type'],
                                                       serializer.validated_data['borrowed_character'])
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
        for member in clanmembers:
            u = member.userinfo.user
            # Get up to 3 characters from the user.
            chars = Character.objects.filter(user=u).order_by('-level')[:3]
            default_loaners = [{'char_id': c.char_id, 'uses_remaining': 9}
                               for c in chars]
            ClanPVEStatus.objects.create(user=u, event=event,
                                         character_lending={'default': True, 'characters': default_loaners})
        return Response({'status': True, 'start_date': target_date})


def get_active_event(clan):
    """Returns either an event in progress or an upcoming event."""
    event = ClanPVEEvent.objects.filter(clan=clan).order_by('-date').first()
    if event and datetime.datetime.today().date() > event.date + datetime.timedelta(days=2):
        event = None
    return event


class ClanPVEStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def get(self, request):
        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of any clans!'})

        event = get_active_event(clan)
        if not event:
            return Response({'status': True, 'has_event': False})
            
        event_status = ClanPVEStatus.objects.filter(user=request.user, event=event).first()
        if not event_status:
            return Response({'status': True, 'has_event': False})

        tickets = None
        if datetime.datetime.today().date() == event.date:
            tickets = event_status.tickets_1
        elif datetime.datetime.today().date() == event.date + datetime.timedelta(days=1):
            tickets = event_status.tickets_2
        elif datetime.datetime.today().date() == event.date + datetime.timedelta(days=2):
            tickets = event_status.tickets_3

        c = Character.objects.get(char_id=event_status.current_borrowed_character)
        # Also load player best scores.
        results = ClanPVEResult.objects.filter(user=request.user)
        scores = [{'boss': r.boss, 'score': r.best_score} for r in results]
        tickets_json = [{'boss': k, 'tickets': tickets[k]} for k in tickets]
        return Response({'status': True, 'has_event': True,
                         'start_time': event.date, 'tickets': tickets_json,
                         'current_boss': str(event_status.current_boss),
                         'current_borrowed_character': CharacterSchema(c).data,
                         'character_lending': event_status.character_lending,
                         'scores': scores,
                         })


class ClanViewLendingView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def get(self, request):
        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of any clans!'})

        event = get_active_event(clan)
        if not event:
            return Response({'status': False, 'reason': 'No active event!'})

        event_statuses = ClanPVEStatus.objects.filter(event=event) \
            .select_related('user__userinfo')
        # Append all the characters from each player's status.
        characters = {}
        for status in event_statuses:
            for c in status.character_lending['characters']:
                characters[c['char_id']] = c['uses_remaining']

        # Actually load all the characters.
        lent_characters = Character.objects.filter(char_id__in=characters.keys()) \
            .select_related('weapon') \
            .select_related('hat') \
            .select_related('armor') \
            .select_related('boots') \
            .select_related('trinket_1') \
            .select_related('trinket_2') 

        # Let's also load the userinfos.
        users = [status.user.userinfo for status in event_statuses]
        return Response({'status': True,
                         'userinfos': LightUserInfoSchema(users, many=True).data,
                         'lent_characters': [{'character': CharacterSchema(c).data, 'uses_remaining': characters[c.char_id]}
                                             for c in lent_characters]
                         })


class ClanLendingSerializer(serializers.Serializer):
    char_1 = serializers.IntegerField()
    char_2 = serializers.IntegerField()
    char_3 = serializers.IntegerField()


class ClanSetLendingView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ClanLendingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        clan = request.user.userinfo.clanmember.clan2
        if not clan:
            return Response({'status': False, 'reason': 'User not part of any clans!'})

        event = get_active_event(clan)
        if not event:
            return Response({'status': False, 'reason': 'No active event!'})

        if datetime.datetime.today().date() >= event.date:
            return Response({'status': False, 'reason': 'After lockin period!'})
        event_status = ClanPVEStatus.objects.filter(user=request.user,
                                                    event=event).first()
        if not event_status:
            return Response({'status': False, 'reason': 'User not enrolled in event!'})

        char_ids = (serializer.validated_data['char_1'],
                    serializer.validated_data['char_2'],
                    serializer.validated_data['char_3'])
        if Character.objects.filter(char_id__in=char_ids, user=request.user).count() != 3:
            return Response({'status': False, 'reason': 'User does not own the charactesr!'})
        
        event_status.character_lending = {'default': False, 'characters': [
            {'char_id': serializer.validated_data['char_1'], 'uses_remaining': 9},
            {'char_id': serializer.validated_data['char_2'], 'uses_remaining': 9},
            {'char_id': serializer.validated_data['char_3'], 'uses_remaining': 9},
        ]}
        event_status.save()
        return Response({'status': True})
        