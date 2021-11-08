from abc import ABC, abstractmethod
from dataclasses import dataclass

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_marshmallow import Schema, fields

from mainsocket import consumers


# Abstract Base Class for getting a Badge Notification count
class BadgeNotifCount(ABC):
    @abstractmethod
    def get_badge_notif(self, user):
        pass


@dataclass(frozen=True)
class BadgeNotif:
    notif_type: int
    amount: int


class BadgeNotifSchema(Schema):
    notif_type = fields.Int()
    amount = fields.Int()


# Sends a list of badge notifs to the websocket
# Replaces the badge count
def send_badge_notifs_replace(user_id, *badge_notifs):
    room_group_name = consumers.notif_channel_group_name(user_id)
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'push_notif',
            'message_type': 'push_notif_replace',
            'data': BadgeNotifSchema(badge_notifs, many=True).data
        }
    )


# Increments the badge count
def send_badge_notifs_increment(user_id, *badge_notifs):
    # Filter out the 0 counts
    badge_notifs = [b for b in badge_notifs if b.amount > 0]
    if len(badge_notifs) == 0:
        return

    room_group_name = consumers.notif_channel_group_name(user_id)
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'push_notif',
            'message_type': 'push_notif_incr',
            'data': BadgeNotifSchema(badge_notifs, many=True).data
        }
    )
