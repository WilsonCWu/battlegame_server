from datetime import datetime, timedelta, timezone
from django.db import transaction

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from mainsocket import notifications
from playerdata import constants
from playerdata.models import EventTimeTracker, GrassEvent


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


def is_event_expired(event_name: str):
    cur_time = datetime.now(timezone.utc)
    event_time = EventTimeTracker.objects.filter(name=event_name).first()
    if event_time is None:
        return True
    return cur_time > event_time.end_time


class GrassEventBadgeNotifCount(notifications.BadgeNotifCount):
    def get_badge_notif(self, user):
        if is_event_expired('grass_event'):
            return notifications.BadgeNotif(constants.NotificationType.GRASS_EVENT.value, 0)

        grass_event, _ = GrassEvent.objects.get_or_create(user=user)
        count = grass_event.unclaimed_tokens
        return notifications.BadgeNotif(constants.NotificationType.GRASS_EVENT.value, count)
