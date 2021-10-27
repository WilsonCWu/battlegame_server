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


class CreatorCodeSchema(Schema):
    creator_code = fields.Str()
    gems_earned = fields.Int()


class CreatorCodeTrackerSchema(Schema):
    code = fields.Nested(CreatorCodeSchema)
    created_time = fields.DateTime()
    is_expired = fields.Boolean()


# Call this whenever gems are spent and creator code should be credited.
def award_supported_creator(user, amountSpent):
    entered_code = CreatorCodeTracker.objects.filter(user=user).first()
    if entered_code is None or entered_code.is_expired or entered_code.code is None:
        return
    earned = int(amountSpent * constants.CREATOR_CODE_SHARED_PERCENT)
    entered_code.code.user.inventory.gems += earned
    entered_code.code.gems_earned += earned
    entered_code.code.save()
    entered_code.code.user.inventory.save()


class CreatorCodeGetView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user_tracker = request.user.creatorcodetracker
        tracker_schema = CreatorCodeTrackerSchema(user_tracker)
        own_creator_code = CreatorCode.objects.filter(user=request.user).first()
        code_schema = CreatorCodeSchema(own_creator_code)

        return Response({'status': True,
                         'creator_code_tracker': tracker_schema.data,
                         'own_code': code_schema.data})


class CreatorCodeChangeView(APIView):
    permission_classes = (IsAuthenticated,)

    @atomic
    def post(self, request):
        serializer = NullableValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entered_code = serializer.validated_data['value']
        current_code = request.user.creatorcodetracker

        if entered_code == "NONE":  # We send "NONE" to clear our current entry.
            current_code.code = None
            current_code.save()
            return Response({'status': True})

        # check if creator code exists and is not owned by request user
        creator_code = CreatorCode.objects.filter(creator_code=entered_code).first()
        if creator_code is None:
            return Response({'status': False, 'reason': 'invalid creator code'})
        if creator_code.user == request.user:
            return Response({'status': False, 'reason': 'cannot enter own code'})

        current_code.code = creator_code
        current_code.created_time = datetime.utcnow()
        current_code.is_expired = False
        current_code.save()
        return Response({'status': True})
