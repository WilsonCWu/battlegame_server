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

from . import chests, constants
from .inventory import CharacterSchema
from .matcher import LightUserInfoSchema
from .models import Character, ClanPVEResult, ClanPVEStatus, ClanPVEEvent, Clan2, ClanMember
from .questupdater import QuestUpdater


class ClanPVEBoss(enum.Enum):
    TheWall = '1'
    OneShotWonder = '2'
    AOEBoss = '3'


class ClanPVESerializer(serializers.Serializer):
    boss_type = serializers.ChoiceField(list((opt.value, opt.name) for opt in ClanPVEBoss))
    score = serializers.IntegerField()
    round_num = serializers.IntegerField()

 
class ClanPVEResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def calculate_rewards(self, boss_type, round_num):
        rewards = []
        total_to_give = 1200

        if boss_type == ClanPVEBoss.TheWall.value:
            boss_difference = -25
        elif boss_type == ClanPVEBoss.OneShotWonder.value:
            boss_difference = 0
        else:
            boss_difference = 25

        geo_sequence = 0.3 * (1.1 ** (round_num - 1)) + 0.1
        percentage = min(geo_sequence, 1)
        relic_stones = math.floor(total_to_give / 9 * percentage)

        relic_stones += boss_difference
        relic_stones += round_num

        rewards.append(chests.ChestReward(reward_type='relic_stone', value=relic_stones))
        return rewards

    def calculate_exp(self, round_num):
        # We expect a clan to make 20 runs to level two, and an additional 60
        # runs to level three. As a result, let's just leave this as one and
        # calculate the level as such.
        return 39 + round_num

    @transaction.atomic
    def post(self, request):
        serializer = ClanPVESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        boss_type = serializer.validated_data['boss_type']
        score = serializer.validated_data['score']
        round_num = serializer.validated_data['round_num']

        # Update the best score for the user if applicable.
        result, _ = ClanPVEResult.objects.get_or_create(
            user=request.user,
            boss=boss_type,
        )

        result.best_score = max(result.best_score, score)
        result.save()

        # Give clan experience per run.
        exp = self.calculate_exp(round_num)
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

        rewards = self.calculate_rewards(boss_type, round_num)
        chests.award_chest_rewards(request.user, rewards)
        reward_schema = chests.ChestRewardSchema(rewards, many=True)

        QuestUpdater.add_progress_by_type(request.user, constants.FIGHT_MONSTER_HUNT, 1)

        return Response({'status': True, 'rewards': reward_schema.data})


CLAN_EXP_BAR = {
    '1': 0,
    '2': 800,
    '3': 3200,
}


def clan_exp_to_level(exp):
    if exp < 800:
        return 1
    elif exp < 3200:
        return 2
    else:
        return 3


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

        # Ensure that you're not borrowing your own character.
        if target_char.user == user:
            return (False, 'Cannot borrow your own character!')

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


ALLOWED_WEEKDAYS = (0, 1, 2, 3)

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

        # Can only start an event if today is M - Th (i.e. events only start
        # from T - F).
        weekday = datetime.date.today().weekday()
        if weekday not in ALLOWED_WEEKDAYS:
            return Response({'status': False, 'reason': 'Can only start event on Mon - Thurs!'})
 
        # Ensure that you don't have an event in the same cycle (i.e. within
        # the last 3 days).
        current_week = datetime.date.today() - datetime.timedelta(days=weekday)
        if ClanPVEEvent.objects.filter(clan=clan, date__gt=current_week).exists():
            return Response({'status': False, 'reason': 'Last event in the same cycle!'})

        target_date = datetime.date.today() + datetime.timedelta(days=1)
        event = ClanPVEEvent.objects.create(clan=clan, date=target_date, started_by=request.user)

        # Generate event statuses for all current clan members.
        clan_query = Clan2.objects.filter(id=clan.id).prefetch_related(Prefetch(
            'clanmember_set', to_attr='clan_members',
            queryset=ClanMember.objects.select_related('userinfo__user')))
        clanmembers = clan_query[0].clan_members
        if len(clanmembers) == 0:
            return Response({'status': False, 'reason': 'Cannot start event for clan of 1!'})

        for member in clanmembers:
            u = member.userinfo.user
            # Prevent the user from clan hoping and entering multiple events
            # per cycle.
            latest_status = ClanPVEStatus.objects.filter(user=u).order_by('-event_id').first()
            if latest_status and latest_status.event.date > current_week:
                continue
 
            # Get up to 3 characters from the user.
            default_loaners = [{'char_id': c, 'uses_remaining': 9}
                               for c in member.pve_character_lending]
            ClanPVEStatus.objects.create(user=u, event=event,
                                         character_lending={'defaulted': True, 'characters': default_loaners})
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
        tickets = {'1': 0, '2': 0, '3': 0}
        if not event_status:
            # BUG: the tickets should be handled client side instead.
            tickets_json = [{'boss': k, 'tickets': tickets[k]} for k in tickets]
            return Response({'status': True, 'has_event': True,
                             'tickets': tickets_json,
                             # BUG: we try to catch empty string on the client,
                             # even though C# actually turns it into null.
                             'start_time': ''})

        if datetime.datetime.today().date() == event.date:
            tickets = event_status.tickets_1
        elif datetime.datetime.today().date() == event.date + datetime.timedelta(days=1):
            tickets = event_status.tickets_2
        elif datetime.datetime.today().date() == event.date + datetime.timedelta(days=2):
            tickets = event_status.tickets_3

        # BUG: If a current boss exists, add 1 to its ticket.
        if event_status.current_boss != -1:
            tickets[str(event_status.current_boss)] += 1

        # A borrowed character may not have been set yet.
        c = Character.objects.filter(char_id=event_status.current_borrowed_character).first()
        c_json = CharacterSchema(c).data if c else None
        # Also load player best scores.
        results = ClanPVEResult.objects.filter(user=request.user)
        scores = [{'boss': r.boss, 'score': r.best_score} for r in results]
        tickets_json = [{'boss': k, 'tickets': tickets[k]} for k in tickets]
        return Response({'status': True, 'has_event': True,
                         'start_time': event.date, 'tickets': tickets_json,
                         'current_boss': str(event_status.current_boss),
                         'current_borrowed_character': c_json,
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

        # Ignore current user, just get the view for the rest of the clan.
        event_statuses = ClanPVEStatus.objects.filter(event=event) \
            .exclude(user=request.user) \
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

        # Validate that the user owns the characters.
        char_ids = [serializer.validated_data['char_1'],
                    serializer.validated_data['char_2'],
                    serializer.validated_data['char_3']]
        if Character.objects.filter(char_id__in=char_ids, user=request.user).count() != 3:
            return Response({'status': False, 'reason': 'User does not own the charactesr!'})

        # Set them to the user's clanmember.
        clanmember = request.user.userinfo.clanmember
        clanmember.pve_character_lending = char_ids
        clanmember.save()

        # If there is an event (before the lock in period, set it as well.)
        event = get_active_event(clan)
        if event and datetime.datetime.today().date() < event.date:
            # Get the user's event status (if it exists).
            event_status = ClanPVEStatus.objects.filter(user=request.user,
                                                        event=event).first()
            if event_status:
                event_status.character_lending = {'defaulted': False, 'characters': [
                    {'char_id': serializer.validated_data['char_1'], 'uses_remaining': 3},
                    {'char_id': serializer.validated_data['char_2'], 'uses_remaining': 3},
                    {'char_id': serializer.validated_data['char_3'], 'uses_remaining': 3},
                ]}
                event_status.save()
        return Response({'status': True})
