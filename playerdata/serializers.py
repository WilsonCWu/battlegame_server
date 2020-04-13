from rest_framework import serializers

class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(required = True)
    password = serializers.CharField(required = True)

class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(required = True)

class CreateNewUserSerializer(serializers.Serializer):
    token = serializers.CharField(required = True)
    name = serializers.CharField(required = True)

class GetUserSerializer(serializers.Serializer):
    target_user = serializers.IntegerField(required = True)

class GetOpponentsSerializer(serializers.Serializer):
    search_count = serializers.IntegerField(required = True)

class UploadResultSerializer(serializers.Serializer):
    win = serializers.BooleanField(required = True)
    mode = serializers.IntegerField(required = True)
    opponent = serializers.IntegerField(required = True)

class LevelUpSerializer(serializers.Serializer):
    target_char_id = serializers.IntegerField(required = True)
