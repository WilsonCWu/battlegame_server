from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import EventTimeTracker


class EventTimeTrackerSchema(Schema):
    event_name = fields.Str()
    start_date = fields.DateTime()
    end_date = fields.DateTime()


class GetEventTimesView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def get(self, request):
        allEventTimes = EventTimeTracker.objects.all()
        return Response({'status': True, 'events': [EventTimeTrackerSchema(p).data for p in allEventTimes]})
