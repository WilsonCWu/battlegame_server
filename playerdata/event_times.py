from datetime import datetime, timedelta
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
        three_months_ago = datetime.now() - timedelta(days=90)
        # don't send trackers for events that ended at least three months ago
        all_trackers = EventTimeTracker.objects.all().filter(end_time__gt=three_months_ago)
        tracker_schema = EventTimeTrackerSchema(all_trackers, many=True)

        return Response({'status': True, 'events': tracker_schema.data})
