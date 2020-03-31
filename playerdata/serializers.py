from rest_framework import serializers

class AuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(required = True)
    password = serializers.CharField(required = True)

class TokenSerializer(serializers.Serializer):
    token = serializers.CharField(required = True)

class CreateNewUserSerializer(serializers.Serializer):
    token = serializers.CharField(required = True)
    name = serializers.CharField(required = True)
