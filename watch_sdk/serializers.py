from rest_framework import serializers
from .models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = "__all__"


class EnabledPlatformSerializer(serializers.ModelSerializer):
    platform = PlatformSerializer()

    class Meta:
        model = EnabledPlatform
        fields = "__all__"


class UserAppSerializer(serializers.ModelSerializer):
    enabled_platforms = EnabledPlatformSerializer(many=True)

    class Meta:
        model = UserApp
        fields = "__all__"


class ConnectedPlatformMetadataSerializer(serializers.ModelSerializer):
    platform = PlatformSerializer()

    class Meta:
        model = ConnectedPlatformMetadata
        fields = "__all__"


class WatchConnectionSerializer(serializers.ModelSerializer):
    connected_platforms = ConnectedPlatformMetadataSerializer(many=True)

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
