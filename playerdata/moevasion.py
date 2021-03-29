from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from .models import MoevasionStatus
from .serializers import MoevasionResultSerializer


class StartView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        status, _ = MoevasionStatus.objects.get_or_create(user=request.user)
        if not status.is_active():
            status.start()
            status.save()
        return Response({'status': True})


class EndView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        try:
            status = MoevasionStatus.objects.get(user=request.user)
        except MoevasionStatus.DoesNotExist:
            return Response({'status': False, 'reason': 'No existing run.'})

        if not status.is_active():
            return Response({'status': False, 'reason': 'No existing run.'})

        status.end()
        status.save()
        return Response({'status': True})


class StageView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        try:
            status = MoevasionStatus.objects.get(user=request.user)
        except MoevasionStatus.DoesNotExist:
            return Response({'status': False, 'reason': 'No existing run.'})

        if not status.is_active():
            return Response({'status': False, 'reason': 'No existing run.'})

        # TODO: add in actual stage. This probably can just be hard coded
        # here.
        return Response({'status': True, 'stage_id': status.stage,
                         'stage': None, 'characters': status.character_state})


class ResultView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = MoevasionResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            status = MoevasionStatus.objects.get(user=request.user)
        except MoevasionStatus.DoesNotExist:
            return Response({'status': False, 'reason': 'No existing run.'})

        if serializer.validated_data['is_loss']:
            status.end()
        else:
            userinfo = request.user.userinfo
            if userinfo.best_moevasion_stage < status.stage:
                userinfo.best_moevasion_stage = status.stage
                userinfo.save()

            status.stage += 1

        status.character_state = serializer.validated_data['characters']
        status.save()
        return Response({'status': True, 'rewards': None})
        
