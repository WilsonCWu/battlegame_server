import secrets
import re

from decouple import config
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.db import transaction
from django.db.transaction import atomic
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_404_NOT_FOUND,
)
from rest_framework.views import APIView

from .serializers import AuthTokenSerializer
from .serializers import CreateNewUserSerializer
from .serializers import ChangeNameSerializer
from .serializers import RecoverAccountSerializer

from .models import UserInfo, IPTracker


class HelloView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        content = {'message': 'Hello, ' + request.user.get_username() + "(" + str(request.user.id) + ")"}
        return Response(content)


class CreateNewUser(APIView):
    throttle_classes = ()
    permission_classes = ()

    @staticmethod
    def generate_password():
        return secrets.token_urlsafe(35)

    @transaction.atomic
    def post(self, request):
        serializer = CreateNewUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data['token']

        if token != config('CREATEUSER_TOKEN'):
            return Response({'detail': 'Invalid Credentials. Please contact support.'}, status=HTTP_401_UNAUTHORIZED)

        latest_id = get_user_model().objects.latest('id').id + 1
        password = CreateNewUser.generate_password()

        user = get_user_model().objects.create_user(username=latest_id, password=password)

        content = {'username': str(latest_id), 'password': password, 'name': latest_id}
        return Response(content)


class ChangeName(APIView):
    throttle_classes = ()
    permission_classes = (IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        serializer = ChangeNameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data['name']

        if "titan" in name.lower() or "salutation studio" in name.lower():
            return Response({'status': False, 'reason': 'Invalid name'})

        if len(name) > 20:
            return Response({'status': False, 'reason': 'Your name cannot be more than 20 characters long'})

        if (re.search(r"\\|\n|\r|[^\x00-\x7F]+", name)): # No backslash, newline, return, or non-basic-ASCII in names.
            return Response({'status': False, 'reason': 'Name contains invalid characters'})

        userinfo = UserInfo.objects.get(user=request.user)
        userinfo.name = name
        userinfo.save()

        return Response({'status': True})


# From https://stackoverflow.com/questions/4581789/how-do-i-get-user-ip-address-in-django
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    else:
        return request.META.get('REMOTE_ADDR')


class ObtainAuthToken(APIView):
    throttle_classes = ()
    permission_classes = ()

    @atomic
    def post(self, request):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        if not user:
            return Response({'detail': 'Invalid Credentials. Please contact support.'}, status=HTTP_401_UNAUTHORIZED)

        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        ip = get_client_ip(request)
        tracker, is_created = IPTracker.objects.get_or_create(ip=ip)
        if user.id not in tracker.user_list:
            tracker.user_list.append(user.id)
            if len(tracker.user_list) > 5:
                tracker.suspicious = True
        tracker.save()

        return Response({'token': token.key, 'user_id': user.id})


class UserRecoveryTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        """Overwrite the hash value to exclude logged-in boolean.

        For our recovery token, we track state based on whether the password
        was changed or not.
        """
        return str(user.pk) + user.password + str(timestamp)


class RecoverAccount(APIView):

    @transaction.atomic
    def post(self, request):
        serializer = RecoverAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user_id = serializer.validated_data['user_id']
            user = get_user_model().objects.get(id=user_id)
        except:
            return Response({'reason': 'failed to get user with id=%s' % user_id}, status=HTTP_404_NOT_FOUND)

        generator = UserRecoveryTokenGenerator()
        if generator.check_token(user, serializer.validated_data['token']):
            new_password = CreateNewUser.generate_password()
            user.set_password(new_password)
            user.save()
            return Response({'password': new_password})
        else:
            return Response({'reason': 'invalid token!'}, status=HTTP_401_UNAUTHORIZED)


class GetRecoveryToken(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        generator = UserRecoveryTokenGenerator()
        return Response({'token': generator.make_token(request.user)})
