from django.db.transaction import atomic
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_marshmallow import Schema, fields

from playerdata import server
from playerdata.models import UserReferral
from playerdata.models import ReferralTracker
from . import constants

from .serializers import ClaimReferralSerializer


class ReferralSchema(Schema):
    referral_code = fields.Str()


def award_referral(user, amount):
    user.inventory.gems += amount
    user.inventory.save()


class ReferralView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        user_ref = UserReferral.objects.get(user=request.user)
        referral_schema = ReferralSchema(user_ref)
        if server.is_server_version_higher('0.5.0'):
            return Response({'status': True, 'referral_code': referral_schema.data})
        return Response(referral_schema.data)

    @atomic
    def post(self, request):
        serializer = ClaimReferralSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        referral_code = serializer.validated_data['referral_code']
        device_id = serializer.validated_data['device_id']

        claimed_referrals = ReferralTracker.objects.filter(user=request.user)
        if claimed_referrals.count() > 0:
            return Response({'status': False, 'reason': 'you have already claimed a referral'})

        # check if referral code exists and is not owned by request user
        user_ref = UserReferral.objects.filter(referral_code=referral_code).first()
        if user_ref is None or user_ref.user == request.user:
            return Response({'status': False, 'reason': 'invalid referral code'})

        # check device id for fraud
        device_referrals = ReferralTracker.objects.filter(device_id=device_id, referral=user_ref)
        # if the save device has redeemed referral for the same user
        if device_referrals.count() > 2:
            # ban device user
            request.user.is_active = False
            request.user.save()

            # ban all of the repeated device accounts (device_referrals)
            num_converted = 0
            for repeat_referral in device_referrals:
                if repeat_referral.converted:
                    num_converted += 1
                repeat_referral.user.is_active = False
                repeat_referral.user.save()

            # subtract earned gems from the repeat accounts on the user_ref side
            user_ref.user.inventory.gems -= num_converted * constants.REFERER_GEMS_REWARD
            user_ref.user.inventory.save()

            return Response({'status': False, 'reason': 'Your account has been banned due to suspicion of referral spam. If you believe this is a mistake, please contact our customer support.'})

        # Award requesting user
        award_referral(request.user, constants.REFEREE_GEMS_REWARD)
        ReferralTracker.objects.create(user=request.user, referral=user_ref, device_id=device_id)

        return Response({'status': True})
