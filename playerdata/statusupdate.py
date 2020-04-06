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

class StatusUpdateView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        win = serializer.validated_data['win']
        mode = serializer.validated_data['mode']
