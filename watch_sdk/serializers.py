from rest_framework import serializers
from .models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class UserAppSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserApp
        fields = "__all__"


class WatchConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchConnection
        fields = "__all__"


class FitnessDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitnessData
        fields = "__all__"


class TestWebhookDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestWebhookData
        fields = "__all__"
