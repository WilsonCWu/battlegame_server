from abc import ABC, abstractmethod

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_marshmallow import Schema, fields

from mainsocket import consumers


# Abstract Base Class for getting a Badge Notification count
class BadgeNotificationCount(ABC):
    @abstractmethod
    def get_count(self, user):
        pass


class BadgeNotif:
    def __init__(self, notif_type, amount):
        self.notif_type = notif_type
        self.amount = amount


class BadgeNotifSchema(Schema):
    notif_type = fields.Int()
    amount = fields.Int()


# Usage: BadgeNotifier(user.id).add_notif(1, 2).add_notif(2, 4).send_notifs()
# Can send multiple badge notifications at once, and delivers it to the client in a json list of BadgeNotifSchema
class BadgeNotifier:
    def __init__(self, user_id):
        self.user_id = user_id
        self.notif_list = []

    def add_notif(self, badge_notif: BadgeNotif):
        self.notif_list.append(badge_notif)
        return self

    def send_notifs(self):
        room_group_name = consumers.notif_channel_group_name(self.user_id)
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'push_notif',
                'data': BadgeNotifSchema(self.notif_list, many=True).data
            }
        )
