from django.db.transaction import atomic
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from playerdata import constants, server
from playerdata.models import UserCreatorCode
from playerdata.models import CreatorCodeTracker

from .serializers import ClaimReferralSerializer


# Call this whenever gems are spent and creator code should be credited.  Checks for creatorCodes, then credits appropriately
def award_supported_creator(user, amountSpent):
    entered_code = CreatorCodeTracker.objects.filter(user=user).first()
    if entered_code is None or entered_code.is_expired:
        return
    entered_code.code.user.inventory.gems += amountSpent * constants.CREATOR_CODE_SHARED_PERCENT
    entered_code.code.user.inventory.save()


# User's side
class CreatorCodeSchema(Schema):
    creator_code = fields.Str()
    code_entered = fields.DateTime()
    is_expired = fields.Bool()


# Used to actually get a user's creator code.
class ReferralView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user_ref: UserCreatorCode = UserCreatorCode.objects.get(user=request.user)
        return Response({'status': True,
                         'creator_code': user_ref.creator_code})


class ReferralUserView(APIView):
    permission_classes = (IsAuthenticated,)

    # Gets status of user's creator code usage.
    def get(self, request):
        current_code = CreatorCodeTracker.objects.filter(user=request.user)
        return Response({'status': True,
                         'creator_code': current_code.code.creator_code,
                         'created_time': current_code.code_entered,
                         'is_expired': current_code.is_expired})

    @atomic
    def post(self, request):
        serializer = ClaimReferralSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        creator_code = serializer.validated_data['creator_code']

        # check if creator code exists and is not owned by request user
        user_ref = UserCreatorCode.objects.filter(creator_code=creator_code).first()
        if user_ref is None or user_ref.user == request.user:
            return Response({'status': False, 'reason': 'invalid creator code'})

        current_code = CreatorCodeTracker.objects.filter(user=request.user)
        if current_code.count() == 0:
            CreatorCodeTracker.objects.create(user=request.user, code=user_ref)
        else:
            current_code.user = request.user, code = user_ref,
        return Response({'status': True})
