from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import HackerAlert, Match

from .serializers import IntSerializer


class UserReportView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        match_id = serializer.validated_data['value']

        # Check that the match still exists.
        q = Match.objects.filter(id=match_id)
        if not q:
            return Response({'status': False, 'reason': 'match does not exist!'})

        match = q[0]
        if request.user.id not in (match.attacker_id, match.defender_id):
            return Response({'status': False, 'reason': 'cannot report someone else\'s match'})
        
        hacker = match.defender if match.attacker_id == request.user.id else match.attacker

        HackerAlert.objects.get_or_create(
            user=hacker,
            reporter=request.user,
            suspicious_match_id=match_id,
        )
        return Response({'status': True})

