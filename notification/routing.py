# notification/routing.py
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/notif/(?P<room_name>\w+)/$', consumers.NotificationConsumer),
]
