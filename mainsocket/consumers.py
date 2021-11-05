# mainsocket/consumers.py
import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer
from rest_marshmallow import Schema, fields

from playerdata import questupdater


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
        room_group_name = notif_channel_group_name(self.user_id)
        channel_layer = get_channel_layer()

        async_to_sync(channel_layer.group_send)(
            room_group_name,
            {
                'type': 'push_notif',
                'data': BadgeNotifSchema(self.notif_list, many=True).data
            }
        )


def notif_channel_group_name(user_id):
    return 'notif_%s' % user_id


# Channel group is the user_id
# Only 1 channel per group, but this is still the convention since group names
# are user defined, channel id's are auto generated and un-gettable
class MainSocketConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = notif_channel_group_name(self.room_name)

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

        # Send current notification badge counts
        BadgeNotifier(self.user.id) \
            .add_notif(questupdater.daily_notifs(self.user)) \
            .add_notif(questupdater.weekly_notifs(self.user)) \
            .add_notif(questupdater.cumulative_notifs(self.user)) \
            .send_notifs()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        pass

    # sends notification amounts to the client socket
    def push_notif(self, event):
        # print(f"push {event['data']}")
        self.send(text_data=json.dumps({
            'message_type': event['type'],
            'data': event['data']
        }))
