from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import event_times
from playerdata.models import GrassEvent, EventTimeTracker
from playerdata.serializers import BooleanSerializer


class GrassEventSchema(Schema):
    cur_floor = fields.Int()
    ladder_index = fields.Int()
    tickets_left = fields.Int()
    tokens_left = fields.Int()
    tokens_bought = fields.Int()


class GetGrassEventView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        event, _ = GrassEvent.objects.get_or_create(user=request.user)
        event_time_tracker = EventTimeTracker.objects.filter(name='grass_event').first()

        return Response({'status': True,
                         'grass_event': GrassEventSchema(event).data,
                         'event_time_tracker': event_times.EventTimeTrackerSchema(event_time_tracker).data
                         })


class StartGrassRunView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        event = GrassEvent.objects.get(user=request.user)

        if event.tickets_left < 1:
            return Response({'status': False, 'reason': 'not enough tickets for a run'})

        event.tickets_left -= 1
        event.save()

        return Response({'status': True})


class FinishGrassRunView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = BooleanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        is_win = serializer.validated_data['value']

        event = GrassEvent.objects.get(user=request.user)

        if is_win:
            event.grass_cuts_left += 1  # TODO: figure out if we want more than 1 per run?
            event.save()

        return Response({'status': True})
