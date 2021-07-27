from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_marshmallow import Schema, fields

from playerdata import redemptioncodes
from playerdata.models import Character, Mail, ClaimedCode
from playerdata.serializers import IntSerializer, CharStateResultSerializer, SendMailSerializer


class MailSchema(Schema):
    message = fields.Str()
    is_read = fields.Bool()

    sender = fields.Str(attribute='sender.userinfo.name')
    sender_id = fields.Int(attribute='sender_id')
    sender_profile_picture_id = fields.Int(attribute='sender_profile_picture_id')
    time_send = fields.DateTime()


class GetInboxView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        all_mail = Mail.objects.filter(receiver=request.user).select_related('sender__userinfo').order_by('-time_send')
        return Response(MailSchema(all_mail, many=True).data)


class ReadInboxView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        mail_id = serializer.validated_data['value']

        mail = Mail.objects.filter(id=mail_id, receiver=request.user).first()
        if mail is None:
            return Response({'status': False, 'reason': 'invalid mail id: ' + mail_id})

        mail.is_read = True
        mail.save()

        return Response({'status': True})


class SendInboxView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = SendMailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        receiver_id = serializer.validated_data['receiver_id']
        message = serializer.validated_data['message']

        pfp_id = request.user.userinfo.profile_picture
        Mail.objects.create(sender=request.user, receiver_id=receiver_id, message=message, sender_profile_picture_id=pfp_id)

        return Response({'status': True})


class ClaimMailView(APIView):
    permission_classes = (IsAuthenticated,)

    @transaction.atomic()
    def post(self, request):
        serializer = IntSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mail_id = serializer.validated_data['value']

        mail = Mail.objects.filter(id=mail_id, receiver=request.user).first()
        if mail is None:
            return Response({'status': False, 'reason': 'invalid mail id: ' + mail_id})

        if ClaimedCode.objects.filter(user=request.user, code=mail.code).exists():
            return Response({'status': False, 'reason': 'code has been redeemed already'})

        redemptioncodes.award_code(request.user, mail.code)
        ClaimedCode.objects.create(user=request.user, code=mail.code)
        redeem_code_schema = redemptioncodes.RedeemCodeSchema(mail.code)
        return Response(redeem_code_schema.data)
