from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from playerdata.models import UserReferral
from playerdata.models import ReferralTracker

from .serializers import ClaimReferralSerializer


def award_referral(user):
    user.inventory.gems += 5000
    user.inventory.save()


class ReferralView(APIView):
    permission_classes = (IsAuthenticated,)

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
        if device_referrals.count() > 3:
            # ban device user + referral user
            request.user.is_active = False
            request.user.save()

            user_ref.user.is_active = False
            user_ref.user.save()

            return Response({'status': False, 'reason': 'Your account has been banned due to suspicion of fraud. If you believe this is a mistake, please contact our customer support.'})

        # Award requesting user
        award_referral(request.user)
        ReferralTracker.objects.create(user=request.user, referral=user_ref, device_id=device_id)

        return Response({'status': True})
