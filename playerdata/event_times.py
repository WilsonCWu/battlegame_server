from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata.models import EventTimeTracker


class EventTimeTrackerSchema(Schema):
    name = fields.Str()
    start_time = fields.DateTime()
    end_time = fields.DateTime()


class GetEventTimesView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def get(self, request):
        all_trackers = EventTimeTracker.objects.all()
        tracker_schema = EventTimeTrackerSchema(all_trackers, many=True)

        return Response({'status': True, 'events': tracker_schema.data})
