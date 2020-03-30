from django.shortcuts import render
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

from .serializers import AuthTokenSerializer

class HelloView(APIView):
    
    permission_classes = (IsAuthenticated,) 

    def get(self, request):
        content = {'message': 'Hello, ' + request.user.get_username() + "(" + str(request.user.id) + ")"}
        return Response(content)

class ObtainAuthToken(APIView):
    
    throttle_classes = ()
    permission_classes = ()

    def post(self, request):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = authenticate(
            username = serializer.validated_data['username'],
            password = serializer.validated_data['password']
        )
        if not user:
            return Response({'detail': 'Invalid Credentials. Please contact support.'}, status=HTTP_404_NOT_FOUND)

        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response({'token': token.key})
