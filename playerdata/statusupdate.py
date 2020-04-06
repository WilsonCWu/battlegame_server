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
from django.contrib.auth import get_user_model

from rest_marshmallow import Schema, fields

# r1, r2 ratings of player 1,2. s1 = 1 if win, 0 if loss, 0.5 for tie
def calculate_elo(r1, r2, s1):
    k = 50 # larger for more volatility
    R1 = 10**(r1/400)
    R2 = 10**(r2/400)
    E1 = R1 / (R1 + R2)
    new_r1 = r1 + k*(s1-E1)
    return new_r1

class StatusUpdateView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = StatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        win = serializer.validated_data['win']
        mode = serializer.validated_data['mode']
        opponent = serializer.validated_data['opponent']
        
        response = {}
        
        if(mode == 0): #quickplay
            otherUser = get_user_model().objects.select_related('userinfo').get(id=opponent)
            updatedRating = calculate_elo(request.user.userinfo.elo, otherUser.userinfo.elo, win)
            response = {"rating":updatedRating}

        return Response(response)

