from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from playerdata.datagetter import BaseCharacterSchema
from playerdata.models import BaseCharacter
from playerdata.models import TournamentMember
from playerdata.models import TournamentTeam
from playerdata.models import TournamentRegistration
from playerdata.models import User
from .purchases import generate_character

from .serializers import SelectCardSerializer
from .serializers import GetCardSerializer
from .serializers import SetDefenceSerializer

import random
from datetime import datetime, date, time, timedelta


# hardcoded list of "bot" user ids
TOURNAMENT_BOTS = [27, 28, 29, 30, 31, 32, 33]


# Tournaments start every week on Thursday
def get_next_tournament_start_time():
    delta = (4 - datetime.today().weekday()) % 7
    if delta is 0:
        delta = 7

    return datetime.combine(date.today(), time()) + timedelta(days=delta)


# Rounds start everyday at 00:00 UTC
def get_next_round_time():
    return datetime.combine(date.today(), time()) + timedelta(days=1)


class TournamentSchema(Schema):
    round = fields.Int()
    round_expiration = fields.DateTime()


class TournamentMemberSchema(Schema):
    group_id = fields.Int()
    tournament = fields.Nested(TournamentSchema)
    defence_placement = fields.Int()
    num_wins = fields.Int()
    num_loses = fields.Int()
    has_picked = fields.Bool()
    rewards_left = fields.Int()
    fights_left = fields.Int()
    is_eliminated = fields.Bool()


# https://books.agiliq.com/projects/django-orm-cookbook/en/latest/random.html
def get_random_from_queryset(num, rarity_odds=None):
    object_set = []
    while len(object_set) < num:
        object_set.append(generate_character(rarity_odds))
    return object_set


class GetCardsView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = GetCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        num_selection = serializer.validated_data['num_cards']

        if num_selection != 5 and num_selection != 3:
            return Response({'status': False, 'reason': 'invalid number of cards requested'})

        # TODO: pass `rarity_odds` as arg to improve the odds of getting rarer Chars near later tourney stages
        card_set = get_random_from_queryset(num_selection)
        card_schema = BaseCharacterSchema(card_set, many=True)
        return Response(card_schema.data)


class SelectCardsView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = SelectCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cards_selection = serializer.validated_data['selection']

        tournament_member = TournamentMember.objects.filter(user=request.user).first()
        if tournament_member is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})
        if tournament_member.round <= 2 and len(cards_selection) != 2 or tournament_member.round > 2 and len(cards_selection) != 1:
            return Response({'status': False, 'reason': 'invalid number of selected cards'})
        if tournament_member.has_picked and tournament_member.rewards_left <= 0:
            return Response({'status': False, 'reason': 'already picked cards'})

        for card in cards_selection:
            TournamentTeam.objects.create(user=request.user, character_id=card)

        if not tournament_member.has_picked:
            tournament_member.has_picked = True
        else:
            tournament_member.rewards_left -= 1
        tournament_member.save()

        return Response({'status': True})


class SetDefense(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = SetDefenceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pos_1 = serializer.validated_data['pos_1']
        char_1 = serializer.validated_data['char_1']
        pos_2 = serializer.validated_data['pos_2']
        char_2 = serializer.validated_data['char_2']
        pos_3 = serializer.validated_data['pos_3']
        char_3 = serializer.validated_data['char_3']
        pos_4 = serializer.validated_data['pos_4']
        char_4 = serializer.validated_data['char_4']
        pos_5 = serializer.validated_data['pos_5']
        char_5 = serializer.validated_data['char_5']

        tournament_member = TournamentMember.objects.filter(user=request.user).first()
        if tournament_member is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})

        tournament_member.defence_placement.pos_1 = pos_1
        tournament_member.defence_placement.char_1 = char_1
        tournament_member.defence_placement.pos_2 = pos_2
        tournament_member.defence_placement.char_2 = char_2
        tournament_member.defence_placement.pos_3 = pos_3
        tournament_member.defence_placement.char_3 = char_3
        tournament_member.defence_placement.pos_4 = pos_4
        tournament_member.defence_placement.char_4 = char_4
        tournament_member.defence_placement.pos_5 = pos_5
        tournament_member.defence_placement.char_5 = char_5
        tournament_member.defence_placement.save()

        return Response({'status': True})


class TournamentMemberView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tournament_member = TournamentMember.objects.filter(user=request.user).first()
        if tournament_member is None:
            tournament_reg = TournamentRegistration.objects.filter(user=request.user).first()
            start_time = get_next_tournament_start_time()
            if tournament_reg is None:
                # Not registered
                return Response({'status': False,
                                 'reason': 'not registered for next tournament',
                                 'tournament': {
                                     'round': -1,
                                     'next_tourney_start_time': start_time
                                 }
                                 })
            else:
                return Response({'status': False,
                                 'reason': 'waiting for tournament to start',
                                 'tournament': {
                                     'round': 0,
                                     'next_tourney_start_time': start_time
                                 }
                                 })

        tournament_schema = TournamentMemberSchema(tournament_member)
        return Response(tournament_schema.data)


class TournamentRegView(APIView):
    permission_classes = (IsAuthenticated,)

    # registration
    def post(self, request):
        tournament_reg = TournamentRegistration.objects.filter(user=request.user).first()
        if tournament_reg is not None:
            return Response({'status': False, 'reason': 'already registered for next tournament'})
        TournamentRegistration.objects.create(user=request.user)
        return Response({'status': True})


class TournamentGroupListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tournament_member = TournamentMember.objects.filter(user=request.user).first()
        if tournament_member is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})

        group_list = TournamentMember.objects.filter(group_id=tournament_member.group_id)
        group_list_schema = TournamentMemberSchema(group_list, many=True)
        return Response(group_list_schema.data)
