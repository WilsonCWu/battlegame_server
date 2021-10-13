from datetime import datetime
from django.db.transaction import atomic
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from .serializers import NullableValueSerializer
from playerdata import constants
from playerdata.models import CreatorCode
from playerdata.models import CreatorCodeTracker


# Call this whenever gems are spent and creator code should be credited.
def award_supported_creator(user, amountSpent):
    entered_code = CreatorCodeTracker.objects.filter(user=user).first()
    if entered_code is None or entered_code.is_expired or entered_code.code.creator_code == "NONE":
        return
    entered_code.code.user.inventory.gems += amountSpent * constants.CREATOR_CODE_SHARED_PERCENT
    entered_code.code.user.inventory.save()


def generate_creator_code(user, code):
    user_code = CreatorCode.objects.create(user=user, creator_code=code)  # Errors if non-unique.
    return user_code


class CreatorCodeSchema(Schema):
    creator_code = fields.Str()


class CreatorCodeStatusSchema(Schema):
    code = fields.Nested(CreatorCodeSchema)
    created_time = fields.DateTime()
    is_expired = fields.Boolean()


class CreatorCodeGetView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user_ref = CreatorCodeTracker.objects.filter(user=request.user).first()
        status_schema = CreatorCodeStatusSchema(user_ref)

        own_code_ref = CreatorCode.objects.filter(user=request.user).first()
        if own_code_ref is None:
            own_code = ""
        else:
            own_code = own_code_ref.creator_code

        if user_ref is None:
            return Response({'status': True})
        return Response({'status': True,
                         'code_status': status_schema.data,
                         'own_code': own_code})


class CreatorCodeChangeView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = NullableValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator_code = serializer.validated_data['value']
        current_code = CreatorCodeTracker.objects.filter(user=request.user)

        if creator_code == "NONE":  # We send "NONE" to clear our current entry.
            if current_code.count() != 0:
                current_code.delete()
            return Response({'status': True})

        # check if creator code exists and is not owned by request user
        user_ref = CreatorCode.objects.filter(creator_code=creator_code).first()
        if user_ref is None:
            return Response({'status': False, 'reason': 'invalid creator code'})
        if user_ref.user == request.user:
            return Response({'status': False, 'reason': 'cannot enter own code'})

        if current_code.count() == 0:
            CreatorCodeTracker.objects.create(user=request.user, code=user_ref, created_time=datetime.utcnow())
        else:
            current_code = current_code.first()
            current_code.user = request.user
            current_code.code = user_ref
            current_code.created_time = datetime.utcnow()
            current_code.is_expired = False
            current_code.save()
        return Response({'status': True})
