from datetime import datetime
from django.db.transaction import atomic
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from .serializers import NullableValueSerializer
from playerdata import constants
from playerdata.models import UserCreatorCode
from playerdata.models import CreatorCodeTracker


# Call this whenever gems are spent and creator code should be credited.  Checks for creatorCodes, then credits appropriately
def award_supported_creator(user, amountSpent):
    entered_code = CreatorCodeTracker.objects.filter(user=user).first()
    if entered_code is None or entered_code.is_expired or entered_code.code.creator_code == "NONE":
        return
    entered_code.code.user.inventory.gems += amountSpent * constants.CREATOR_CODE_SHARED_PERCENT
    entered_code.code.user.inventory.save()


def generate_creator_code(user, code):
    user_code = UserCreatorCode.objects.create(user=user, creator_code=code)  # Errors if non-unique.
    return user_code


# User's side
class CreatorCodeSchema(Schema):
    creator_code = fields.Str()
    code_entered = fields.DateTime()
    is_expired = fields.Bool()


# Used to actually get a user's creator code.
class CreatorCodeGetView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user_ref = UserCreatorCode.objects.filter(user=request.user).first()
        if user_ref is None:
            generate_creator_code(request.user, 'TEST')  # TEMP
            return Response({'status': True,
                             'creator_code': 'NONE'})
        return Response({'status': True,
                         'creator_code': user_ref.creator_code})


class CreatorCodeStatusView(APIView):
    permission_classes = (IsAuthenticated,)

    # Gets status of user's creator code usage.
    def get(self, request):
        current_code = CreatorCodeTracker.objects.filter(user=request.user).first()
        if current_code is None:
            return Response({'status': True,
                             'creator_code': "",
                             'created_time': "",
                             'is_expired': False})

        return Response({'status': True,
                         'creator_code': current_code.code.creator_code,
                         'created_time': current_code.code_entered,
                         'is_expired': current_code.is_expired})


class CreatorCodeChangeView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = NullableValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator_code = serializer.validated_data['value']
        current_code = CreatorCodeTracker.objects.filter(user=request.user)

        if creator_code == "NONE":
            if current_code.count() != 0:
                current_code.delete()
            return Response({'status': True})

        # check if creator code exists and is not owned by request user
        user_ref = UserCreatorCode.objects.filter(creator_code=creator_code).first()
        if user_ref is None or user_ref.user == request.user:
            return Response({'status': False, 'reason': 'invalid creator code'})

        if current_code.count() == 0:
            CreatorCodeTracker.objects.create(user=request.user, code=user_ref, code_entered=datetime.utcnow())
        else:
            current_code.user = request.user, current_code.code = user_ref,
        return Response({'status': True})
