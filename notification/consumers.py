# notification/consumers.py
import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels.layers import get_channel_layer


def notif_channel_group_name(user_id):
    return 'notif_%s' % user_id


def send_notification(user_id, notif_type, amount):
    room_group_name = notif_channel_group_name(user_id)
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        room_group_name,
        {
            'type': 'push_notif',
            'notif_type': notif_type,
            'amount': amount
        }
    )


# Channel group is the user_id
# Only 1 channel per group, but this is still the convention since group names
# are user defined, channel id's are not
class NotificationConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = notif_channel_group_name(self.room_name)

        print(f'Group name {self.room_group_name}')

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

        # TODO: we can move all our notif badge counts to redis, except qureying db for the init
        # Send current notification badge counts
        self.send(text_data=json.dumps({
            'notif_type': 12,
            'amount': 32
        }))

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Don't receive anything from other side only use this websocket to push new notification badge numbers
    def receive(self, text_data):
        print(text_data)
        pass

    # sends notification amounts to the client socket
    def push_notif(self, event):
        notif_type = event['notif_type']
        amount = event['amount']

        self.send(text_data=json.dumps({
            'notif_type': notif_type,
            'amount': amount
        }))
