from rest_framework import serializers


class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)


class CreateNewUserSerializer(serializers.Serializer):
    token = serializers.CharField(required=True)
    name = serializers.CharField(required=True)


class GetUserSerializer(serializers.Serializer):
    target_user = serializers.IntegerField(required=True)


class GetOpponentsSerializer(serializers.Serializer):
    search_count = serializers.IntegerField(required=True)


class UploadResultSerializer(serializers.Serializer):
    result = serializers.JSONField()


class LevelUpSerializer(serializers.Serializer):
    target_char_id = serializers.IntegerField(required=True)


class PurchaseSerializer(serializers.Serializer):
    purchase_id = serializers.CharField(required=True)


class PurchaseItemSerializer(serializers.Serializer):
    purchase_item_id = serializers.CharField(required=True)


class ValueSerializer(serializers.Serializer):
    value = serializers.CharField(required=True)


class NullableValueSerializer(serializers.Serializer):
    value = serializers.CharField(required=True, allow_blank=True)


class NewClanSerializer(serializers.Serializer):
    clan_name = serializers.CharField(required=True)
    clan_description = serializers.CharField(required=True)


class AcceptFriendRequestSerializer(serializers.Serializer):
    accept = serializers.BooleanField(required=True)
    target_id = serializers.IntegerField(required=True)


class UpdateClanMemberStatusSerializer(serializers.Serializer):
    member_id = serializers.IntegerField(required=True)
    member_status = serializers.CharField(required=True)


class UpdateClanRequestSerializer(serializers.Serializer):
    target_user_id = serializers.IntegerField(required=True)
    accept = serializers.BooleanField(required=True)


class GetDungeonProgressSerializer(serializers.Serializer):
    target_user = serializers.IntegerField(required=True)


class GetDungeonStageSerializer(serializers.Serializer):
    stage_id = serializers.IntegerField(required=True)