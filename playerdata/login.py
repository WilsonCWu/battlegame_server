import secrets

from decouple import config
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_404_NOT_FOUND,
)
from rest_framework.views import APIView

from .serializers import AuthTokenSerializer
from .serializers import CreateNewUserSerializer
from .serializers import ChangeNameSerializer

from .models import UserInfo


class HelloView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        content = {'message': 'Hello, ' + request.user.get_username() + "(" + str(request.user.id) + ")"}
        return Response(content)


class CreateNewUser(APIView):
    throttle_classes = ()
    permission_classes = ()

    def post(self, request):
        serializer = CreateNewUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        if token != config('CREATEUSER_TOKEN'):
            return Response({'detail': 'Invalid Credentials. Please contact support.'}, status=HTTP_404_NOT_FOUND)

        latest_id = get_user_model().objects.latest('id').id + 1
        password = secrets.token_urlsafe(35)

        user = get_user_model().objects.create_user(username=latest_id, password=password)

        content = {'username': str(latest_id), 'password': password, 'name': latest_id}
        return Response(content)


class ChangeName(APIView):
    throttle_classes = ()
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ChangeNameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data['name']

        userinfo = UserInfo.objects.get(user=request.user)
        userinfo.name = name
        userinfo.save()

        return Response({'status': True})


class ObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()

    def post(self, request):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        if not user:
            return Response({'detail': 'Invalid Credentials. Please contact support.'}, status=HTTP_404_NOT_FOUND)

        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response({'token': token.key, 'user_id': user.id})
