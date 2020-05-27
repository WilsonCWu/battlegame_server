# chat/routing.py
from django.urls import re_path
from . import consumers
from . import videoparty

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_name>\w+)/$', consumers.ChatConsumer),
    re_path(r'ws/videoparty/(?P<room_name>\w+)/$', videoparty.PartyConsumer),
]
