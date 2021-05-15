import collections

from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import HackerAlert, Match, Character

from .serializers import IntSerializer


class UserReportView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        match_id = serializer.validated_data['value']

        # Check that the match still exists.
        match = Match.objects.filter(id=match_id).first()
        if not match:
            return Response({'status': False, 'reason': 'match does not exist!'})

        if request.user.id not in (match.attacker_id, match.defender_id):
            return Response({'status': False, 'reason': 'cannot report someone else\'s match'})
        
        hacker = match.defender if match.attacker_id == request.user.id else match.attacker

        HackerAlert.objects.get_or_create(
            user=hacker,
            reporter=request.user,
            suspicious_match_id=match_id,
        )
        return Response({'status': True})


class MatchValidator:
    """MatchValidator looks for inconsistencies between a user's match and
    their inventory."""

    DEFAULT_SAMPLE_RATE = 3

    def __init__(self, sample_rate=DEFAULT_SAMPLE_RATE):
        self.sample_rate=sample_rate

    def validate(self, match, replay):
        if match.id % self.sample_rate != 0:
            return

        MatchValidator._validate_user(match.id, match.attacker, replay.attacking_team)
        MatchValidator._validate_user(match.id, match.defender, replay.defending_team)

    def _validate_user(match_id, user, payload):
        battle_chars = MatchValidator._chars_from_payload(payload)
        inv_chars = {c.char_id: c for c in Character.objects.filter(user=user)}

        reason = None
        for c in battle_chars:
            if c.char_id not in inv_chars:
                reason = "used char_id %d which is not in inventory" % c.char_id
                break
            inv_char = inv_chars[c.char_id]
            if inv_char.char_type != c.char_type:
                reason = "char_id's type mismatched from %d to %d" % (inv_char.char_type, c.char_type)
                break
            if inv_char.level < c.level:
                reason = "inventory char level is lower than match's"
                break
            if inv_char.prestige < c.prestige:
                reason = "inventory prestige level is lower than match's"
                break

        if reason:
            HackerAlert.objects.create(
                user=user,
                suspicious_match_id=match_id,
                notes=reason + '\n\n' + str(payload)
            )

    def _chars_from_payload(payload):
        """Extract characters from a Placement payload."""
        PayloadChar = collections.namedtuple('PayloadChar',
                                             ['char_type', 'char_id', 'level', 'prestige'])
        for i in range(1, 6):
            pos_key = 'pos_' + str(i)
            if payload[pos_key] != -1:
                char_json = payload['char_' + str(i)]
                yield PayloadChar(**{f: char_json[f] for f in char_json if f in PayloadChar._fields})

