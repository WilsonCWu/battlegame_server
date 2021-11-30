# chat/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from rest_marshmallow import Schema, fields
from better_profanity import profanity

from playerdata.models import ChatMessage
from playerdata.models import Chat
from playerdata.models import ChatLastReadMessage

profanity.load_censor_words(whitelist_words=['omg', 'omfg', 'lmao', 'lmfao', 'god', 'goddamn', 'goddammit', 'goddamned',
                                             'pee', 'poop', 'suck', 'sucked', 'crap', 'turd', 'piss', 'ugly', 'vulgar',
                                             'womb', 'virgin', 'retard', 'moron', 'doofus', 'dummy', 'douche',
                                             'douchebag', 'gay', 'lesbian', 'damn', 'fart', 'fat', 'hell', 'quicky',
                                             'sexual', 'wtf', 'kill', 'jerk', 'vomit', 'vulgar', 'vodka', 'wang',
                                             'weirdo', 'xx', 'xxx', 'urinal', 'urine', 'unwed', 'thug', 'stupid',
                                             'strip', 'steamy', 'sissy', 'seduce', 'pot'])


def censor_referral(message: str):
    tokens = message.split(' ')

    for tok in tokens:
        if tok.isupper() and len(tok) == 12:
            return "****"

    return message


class MessageSchema(Schema):
    message = fields.Str()
    # TODO: this is quite expensive, should not be in here
    sender = fields.Str(attribute='sender.userinfo.name')
    sender_id = fields.Int(attribute='sender_id')
    sender_profile_picture_id = fields.Int(attribute='sender_profile_picture_id')
    time_send = fields.DateTime()


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name

        if not self.room_name.isdigit():
            raise Exception('<h1>room ' + self.room_name + ' must be an int</h1>')

        chatSet = Chat.objects.filter(id=int(self.room_name))

        if not chatSet:
            raise Exception('<h1>room ' + self.room_name + ' not found</h1>')

        self.chat = chatSet[0]

        # Join room group
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json['message_type']

        if message_type == 'msg':
            message = profanity.censor(text_data_json['message'])
            message = censor_referral(message)

            pfp_id = self.user.userinfo.profile_picture
            replay_id = -1
            if hasattr(text_data_json, 'replay_id'):
                replay_id = text_data_json['replay_id']

            # Send message to room group
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender': self.user.userinfo.name,
                    'sender_profile_picture_id': pfp_id,
                    'replay_id': replay_id
                }
            )

            # save to db
            chat_message = ChatMessage.objects.create(chat=self.chat, message=message, sender=self.user,
                                                      sender_profile_picture_id=pfp_id, replay_id=replay_id)
            ChatLastReadMessage.objects.update_or_create(chat=self.chat,
                                                         user=self.user,
                                                         defaults={"time_send": chat_message.time_send}
                                                         )

        elif message_type == 'req':
            latest_timestamp = text_data_json['latest_timestamp']

            if not latest_timestamp:
                old_message_set_partial = ChatMessage.objects.filter(chat=self.chat)
            else:
                old_message_set_partial = ChatMessage.objects.filter(chat=self.chat, time_send__lt=latest_timestamp)

            old_message_set = old_message_set_partial.order_by('-time_send').select_related('sender__userinfo')[:30]
            old_message_json = MessageSchema(old_message_set, many=True)

            last_read_msg = ChatLastReadMessage.objects.filter(chat=self.chat, user=self.user).first()
            latest_msg = old_message_set.first()

            if not last_read_msg:
                show_badge = 'true'
            elif not latest_msg:
                show_badge = 'false'
            else:
                show_badge = not latest_timestamp and (latest_msg.time_send > last_read_msg.time_send)

            self.send(text_data=json.dumps({
                'message_type': 'msgs',
                'msgs': old_message_json.data,
                'show_badge': show_badge
            }))

        elif message_type == 'last_read':
            latest_timestamp = text_data_json['latest_timestamp']
            ChatLastReadMessage.objects.update_or_create(chat=self.chat,
                                                         user=self.user,
                                                         defaults={"time_send": latest_timestamp}
                                                         )

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        sender = event['sender']
        sender_profile_picture_id = event['sender_profile_picture_id']
        replay_id = event['replay_id']
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id,
            'sender': sender,
            'sender_profile_picture_id': sender_profile_picture_id,
            'replay_id': replay_id
        }))
