import math
import random 

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
from playerdata.datagetter import BaseCharacterSchema
from playerdata.models import Inventory
from playerdata.models import Character
from playerdata.models import BaseCharacter

from .serializers import PurchaseSerializer
from .serializers import PurchaseItemSerializer

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

def generateCharacter():
    
    odds = [5,15,30,100]
    val = random.randrange(10000)/100

    for i in range(0, len(odds)):
        if val <= odds[i]:
            rarity = len(odds)-i
            break

    baseChars = BaseCharacter.objects.filter(rarity=rarity)
    numChars = baseChars.count()

    chosenChar = baseChars[random.randrange(numChars)]

    return chosenChar


def insert_character(user, chosen_char):
    old_char = Character.objects.filter(user=user, char_type=chosen_char).first()

    if old_char:
        old_char.copies += 1
        old_char.save()
        return

    Character.objects.create(user=user, char_type=chosen_char)

class PurchaseItemView(APIView):
    
    permission_classes = (IsAuthenticated,)

    def post(self, request):

        serializer = PurchaseItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        purchase_item_id = serializer.validated_data['purchase_item_id']

        if purchase_item_id == "chars10":
            user = request.user
            
            # check enough gems
            inventory = Inventory.objects.get(user=user)
            if inventory.gems < 1000:
                return Response({"status":1, "reason":"not enough gems"})

            inventory.gems -= 1000
            inventory.save()

            newCharTypes = []

            for i in range(0,10):
                newChar = generateCharacter()
                insert_character(user, newChar)
                newCharTypes.append(newChar.char_type)
            
            return Response({"status":0, "characters":newCharTypes})
