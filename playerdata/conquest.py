import math
import random
from datetime import date, datetime, timedelta

from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from .models import RogueAllowedAbilities


class AllowedAbilitySchema(Schema):
    char_id = fields.Int()
    ability_type = fields.Char()


class AllAllowedAbilities(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        return AllowedAbilitySchema(RogueAllowedAbilities.objects.filter(allowed=True),
                                    many=True).data
