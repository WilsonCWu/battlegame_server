from django.db.models import Max
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from playerdata.datagetter import BaseCharacterSchema
from playerdata.models import BaseCharacter
from playerdata.models import Tournament
from playerdata.models import TournamentTeam
from playerdata.models import User

from .serializers import SelectCardSerializer
from .serializers import GetCardSerializer
from .serializers import SetDefenceSerializer

import random


class TournamentSchema(Schema):
    group_id = fields.Int()
    defence_placement = fields.Int()
    num_wins = fields.Int()
    num_loses = fields.Int()
    round = fields.Int()
    has_picked = fields.Bool()
    rewards_left = fields.Int()


# https://books.agiliq.com/projects/django-orm-cookbook/en/latest/random.html
def get_random_from_queryset(model, num, id='id'):
    max_id = model.objects.all().aggregate(max_id=Max(id))['max_id']
    object_set = []
    while len(object_set) < num:
        pk = random.randint(1, max_id)
        instance = model.objects.filter(pk=pk).first()
        if instance:
            object_set.append(instance)
    return object_set


class GetCardsView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = GetCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        num_selection = serializer.validated_data['num_cards']

        if num_selection != 5 and num_selection != 3:
            return Response({'status': False, 'reason': 'invalid number of cards requested'})

        card_set = get_random_from_queryset(BaseCharacter, num_selection, 'char_type')
        card_schema = BaseCharacterSchema(card_set, many=True)
        return Response(card_schema.data)


class SelectCardsView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = SelectCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cards_selection = serializer.validated_data['selection']

        tournament = Tournament.objects.filter(user=request.user).first()
        if tournament is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})
        if tournament.round <= 2 and len(cards_selection) != 2 or tournament.round > 2 and len(cards_selection) != 1:
            return Response({'status': False, 'reason': 'invalid number of selected cards'})
        if tournament.has_picked and tournament.rewards_left <= 0:
            return Response({'status': False, 'reason': 'already picked cards'})

        for card in cards_selection:
            TournamentTeam.objects.create(user=request.user, character_id=card)

        if not tournament.has_picked:
            tournament.has_picked = True
        else:
            tournament.rewards_left -= 1
        tournament.save()

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

        tournament = Tournament.objects.filter(user=request.user).first()
        if tournament is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})

        tournament.defence_placement.pos_1 = pos_1
        tournament.defence_placement.char_1 = char_1
        tournament.defence_placement.pos_2 = pos_2
        tournament.defence_placement.char_2 = char_2
        tournament.defence_placement.pos_3 = pos_3
        tournament.defence_placement.char_3 = char_3
        tournament.defence_placement.pos_4 = pos_4
        tournament.defence_placement.char_4 = char_4
        tournament.defence_placement.pos_5 = pos_5
        tournament.defence_placement.char_5 = char_5
        tournament.defence_placement.save()

        return Response({'status': True})


class TournamentView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tournament = Tournament.objects.filter(user=request.user).first()
        if tournament is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})
        tournament_schema = TournamentSchema(tournament)
        return Response(tournament_schema.data)
