import random
from datetime import date, datetime, timedelta

from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from .serializers import CharStateResultSerializer
from .models import RotatingModeStatus


class RotatingModeStatusSchema(Schema):
    stage = fields.Int()
    character_state = fields.Str()
    rewards_claimed = fields.Int()


def get_next_refresh_time():
    return


class RotatingModeStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        status = RotatingModeStatus.objects.get(user=request.user)
        return Response({'status': RotatingModeStatusSchema(status).data,
                         'next_refresh_time': get_next_refresh_time()})


def rotating_mode_stage_generator(stage: int):
    return


class RotatingModeStageView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        status = RotatingModeStatus.objects.get(user=request.user)
        return Response({'status': True, 'stage_id': status.stage, 'mob': rotating_mode_stage_generator(status.stage)})


def rotating_mode_reward(stage: int, user):
    return []


def get_rotating_mode_max_stages():
    return 80


class RotatingModeResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = CharStateResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        status = RotatingModeStatus.objects.get(user=request.user)
        status.character_state = serializer.validated_data['characters']

        if serializer.validated_data['is_loss']:
            status.stage = 1
        else:
            if status.stage == get_rotating_mode_max_stages:
                status.stage = 1
                status.character_state = ""
            else:
                status.stage += 1

        status.save()
        return Response({'status': True})


class ClaimRotatingModeRewardView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        status = RotatingModeStatus.objects.get(user=request.user)
        status.rewards_claimed += 1
        status.save()

        rewards = rotating_mode_reward(status.stage, request.user)
        return Response({'status': True, 'rewards': rewards})
