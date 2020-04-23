# chat/consumers.py
import json
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from rest_marshmallow import Schema, fields

from playerdata.models import ChatMessage
from playerdata.models import Chat

class MessageSchema(Schema):
    message = fields.Str()
    sender = fields.Str(attribute='sender.userinfo.name')
    sender_id = fields.Int(attribute='sender_id')
    time_send = fields.DateTime()

class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.user = self.scope["user"]
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = 'chat_%s' % self.room_name
       
        if not self.room_name.isdigit():
            raise Exception('<h1>room '+self.room_name+' must be an int</h1>')
        
        chatSet = Chat.objects.filter(id=int(self.room_name))
        
        if not chatSet:
            raise Exception('<h1>room '+self.room_name+' not found</h1>')

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
            message = text_data_json['message']

            # Send message to room group
            async_to_sync(self.channel_layer.group_send)(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender': self.user.userinfo.name
                }
            )

            # save to db
            ChatMessage.objects.create(chat=self.chat, message=message, sender=self.user)
        
        elif message_type == 'req':
            latest_timestamp = text_data_json['latest_timestamp']

            if not latest_timestamp:
                oldMessageSetPartial = ChatMessage.objects.filter(chat=self.chat)
            else:
                oldMessageSetPartial = ChatMessage.objects.filter(chat=self.chat, time_send__lt=latest_timestamp)

            oldMessageSet = oldMessageSetPartial.order_by('time_send').select_related('sender__userinfo')[:30]
            oldMessageJson = MessageSchema(oldMessageSet, many=True)
            self.send(text_data=json.dumps({
                'message_type': 'msgs',
                'msgs': oldMessageJson.data
            }))

    # Receive message from room group
    def chat_message(self, event):
        message = event['message']
        sender_id = event['sender_id']
        sender = event['sender']
        # Send message to WebSocket
        self.send(text_data=json.dumps({
            'message': message,
            'sender_id': sender_id,
            'sender': sender
        }))
