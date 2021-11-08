# mainsocket/consumers.py
import json

from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from mainsocket import notifications
from playerdata import questupdater


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
        notifications.send_badge_notifs_replace(self.user.id,
                                                questupdater.DailyBadgeNotifCount().get_badge_notif(self.user),
                                                questupdater.WeeklyBadgeNotifCount().get_badge_notif(self.user),
                                                questupdater.CumulativeBadgeNotifCount().get_badge_notif(self.user)
                                                )

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
            'message_type': event['message_type'],
            'data': event['data']
        }))
