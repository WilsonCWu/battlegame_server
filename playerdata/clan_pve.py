"""Clan PVE

Design doc:
https://docs.google.com/document/d/1oG73A93V7ZO6e3CWrwM1yHKWOW9lGHGCxuyuJiwgjMs/edit.
"""

import enum

from django.db import transaction
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from .models import ClanPVEResult


class ClanPVEBoss(enum.Enum):
    TheWall = '1'
    OneShotWonder = '2'
    AOEBoss = '3'


class ClanPVESerializer(serializers.Serializer):
    boss_type = serializers.ChoiceField(list((opt.value, opt.name) for opt in ClanPVEBoss))
    score = serializers.IntegerField()


# TODO: APIs for character lending.
# TODO: APIs for unlocking game modes by clan EXP.
    
class ClanPVEResultView(APIView):
    permission_classes = (IsAuthenticated,)

    def calculate_rewards(self):
        pass

    def calculate_exp(self):
        pass

    @transaction.atomic
    def post(self, request):
        serializer = ClanPVESerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Update the best score for the user if applicable.
        result, _ = ClanPVEResult.objects.get_or_create(
            user=request.user,
            boss=serializer.validated_data['boss_type'],
        )
        result.best_score = max(result.best_score, serializer.validated_data['score'])
        result.save()

        rewards = self.calculate_rewards()
        exp = self.calculate_exp()

        return Response({'status': True})

