import math

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

from playerdata.models import Inventory

from .serializers import PurchaseSerializer

# TODO: verify these purchases serverside
class PurchaseView(APIView):

    permission_classes = (IsAuthenticated,)

    def post(self, request):
        
        serializer = PurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_id = serializer.validated_data['purchase_id']
       
        inventory = Inventory.objects.get(user=request.user)
        
        if purchase_id == 'com.battlegame.gems300':
            inventory.gems += 300

        else:
            return Response({'status':False, 'reason':'invalid id ' + purchase_id})

        inventory.save()

        return Response({'status':True})


