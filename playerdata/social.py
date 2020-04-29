from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from rest_framework.decorators import api_view, permission_classes
from rest_framework.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_200_OK,
)
from django.contrib.auth import authenticate
from django.http import JsonResponse

from rest_marshmallow import Schema, fields

from playerdata.models import Friend
from playerdata.models import FriendRequest
from .serializers import GetUserSerializer

class FriendSchema(Schema):
    user_id = fields.Int(attribute='user_id')
    friend_id = fields.Int(attribute='friend_id')
    chat_id = fields.Int(attribute='chat_id')

class FriendRequestSchema(Schema):
    user_id = fields.Int(attribute='user_id')
    target_id = fields.Int(attribute='target_id')

class FriendsView(APIView):

    permission_classes = (IsAuthenticated,)

    def get(self, request):
        query = Friend.objects.filter(user=request.user)
        friends = FriendSchema(query, many=True)
        return Response({'friends':friends.data})

