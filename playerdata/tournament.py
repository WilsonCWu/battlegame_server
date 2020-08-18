from datetime import datetime, date, time, timedelta

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import TournamentMember
from playerdata.models import TournamentRegistration
from playerdata.models import TournamentTeam
from playerdata.models import TournamentSelectionCards
from playerdata.models import TournamentMatch
from .matcher import UserInfoSchema, PlacementSchema
from .purchases import generate_character
from .serializers import GetCardSerializer
from .serializers import SelectCardSerializer
from .serializers import SetDefenceSerializer

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
    id = fields.Int()
    round = fields.Int()
    round_expiration = fields.DateTime()


class TournamentMemberSchema(Schema):
    defence_placement_id = fields.Int()
    num_wins = fields.Int()
    num_losses = fields.Int()
    has_picked = fields.Bool()
    rewards_left = fields.Int()
    fights_left = fields.Int()
    is_eliminated = fields.Bool()


class GroupListSchema(Schema):
    userinfo = fields.Nested(UserInfoSchema, attribute='user.userinfo')
    name = fields.Str(attribute='user.username')
    num_wins = fields.Int()
    num_losses = fields.Int()
    is_eliminated = fields.Bool()


class TournamentMatchSchema(Schema):
    defender = fields.Nested(GroupListSchema)
    placement = fields.Nested(PlacementSchema, attribute='defender.defence_placement')


class TournamentMatchHistorySchema(Schema):
    opponent = fields.Nested(UserInfoSchema)
    is_attacker = fields.Bool()
    is_win = fields.Bool()
    name = fields.Str()


# https://books.agiliq.com/projects/django-orm-cookbook/en/latest/random.html
def get_random_from_queryset(num, rarity_odds=None):
    object_set = []
    while len(object_set) < num:
        new_char = generate_character(rarity_odds)
        object_set.append(new_char.char_type)
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
        card_set = TournamentSelectionCards.objects.filter(user=request.user).first()
        if card_set is None:
            card_set = get_random_from_queryset(num_selection)
            TournamentSelectionCards.objects.create(user=request.user, cards=card_set)
        else:
            card_set = card_set.cards
        return Response({'cards': card_set})


class SelectCardsView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = SelectCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cards_selection = serializer.validated_data['selection']['cards']

        tournament_member = TournamentMember.objects.filter(user=request.user).first()
        if tournament_member is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})
        if tournament_member.has_picked and tournament_member.rewards_left <= 0:
            return Response({'status': False, 'reason': 'already picked cards'})

        if not tournament_member.has_picked:
            if tournament_member.tournament.round <= 2 and len(cards_selection) != 2 or tournament_member.tournament.round > 2 and len(cards_selection) != 1:
                return Response({'status': False, 'reason': 'invalid number of selected cards'})
            tournament_member.has_picked = True
        else:
            if len(cards_selection) != 1:
                return Response({'status': False, 'reason': 'invalid number of selected cards'})
            tournament_member.rewards_left -= 1
        tournament_member.save()

        card_set = TournamentSelectionCards.objects.filter(user=request.user).first()
        for card in cards_selection:
            if card in card_set.cards:
                card_set.cards.remove(card)
            else:
                return Response({'status': False, 'reason': 'invalid card selection'})

        for card in cards_selection:
            TournamentTeam.objects.create(user=request.user, character_id=card)

        TournamentSelectionCards.objects.get(user=request.user).delete()

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


class TournamentView(APIView):
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
                                 'has_joined': False,
                                 'next_tourney_start_time': start_time
                                 })
            else:
                return Response({'status': False,
                                 'reason': 'waiting for tournament to start',
                                 'has_joined': True,
                                 'next_tourney_start_time': start_time
                                 })

        group_list = TournamentMember.objects.filter(tournament=tournament_member.tournament).order_by('-is_eliminated', '-num_wins')
        group_list_schema = GroupListSchema(group_list, many=True)
        me = TournamentMemberSchema(tournament_member)
        tourney = TournamentSchema(tournament_member.tournament)
        return Response({'group_list': group_list_schema.data, 'tournament': tourney.data, 'me': me.data})


class TournamentRegView(APIView):
    permission_classes = (IsAuthenticated,)

    # registration
    def post(self, request):
        tournament_reg = TournamentRegistration.objects.filter(user=request.user).first()
        if tournament_reg is not None:
            return Response({'status': False, 'reason': 'already registered for next tournament'})
        TournamentRegistration.objects.create(user=request.user)
        return Response({'status': True})


class TournamentFightsView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tournament_member = TournamentMember.objects.filter(user=request.user).first()
        if tournament_member is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})

        round_num = tournament_member.tournament.round - 1
        matches = TournamentMatch.objects.filter(attacker=tournament_member, round=round_num, has_played=False)
        matches_schema = TournamentMatchSchema(matches, many=True)

        return Response({"matches": matches_schema.data})


class TournamentMatchHistory(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tournament_member = TournamentMember.objects.filter(user=request.user).first()
        if tournament_member is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})

        attacking_matches = TournamentMatch.objects.filter(attacker=tournament_member, has_played=True)
        defending_matches = TournamentMatch.objects.filter(defender=tournament_member, has_played=True)
        merged_matches = (attacking_matches | defending_matches).order_by('-round')
        matches = []

        for match_query in merged_matches:
            match = {
                'is_attacker': match_query.attacker == tournament_member,
                'is_win': match_query.is_win
            }

            if match_query.attacker == tournament_member:
                match['opponent'] = match_query.defender.user.userinfo
                match['name'] = match_query.defender.user.username
            else:
                match['opponent'] = match_query.attacker.user.userinfo
                match['name'] = match_query.attacker.user.username

            matches.append(match)

        matches_schema = TournamentMatchHistorySchema(matches, many=True)
        return Response({"matches": matches_schema.data})


class TournamentSelfView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        tournament_member = TournamentMember.objects.filter(user=request.user).first()
        if tournament_member is None:
            return Response({'status': False, 'reason': 'not competing in current tournament'})

        placement_schema = PlacementSchema(tournament_member.defence_placement)

        return Response({"name": request.user.username,
                         "elo": request.user.userinfo.tourney_elo,
                         "team": placement_schema.data})
