from rest_framework import serializers
from .models import *


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = "__all__"


class PlatformSerializer(serializers.ModelSerializer):
    class Meta:
        model = Platform
        fields = ["name", "id"]


class EnabledPlatformSerializer(serializers.ModelSerializer):
    platform_name = serializers.SerializerMethodField()

    def get_platform_name(self, obj):
        return obj.platform.name

    class Meta:
        model = EnabledPlatform
        fields = ["platform_name", "platform_app_id"]


class UserAppSerializer(serializers.ModelSerializer):
    enabled_platforms = EnabledPlatformSerializer(many=True, read_only=True)

    class Meta:
        model = UserApp
        fields = "__all__"


class ConnectedPlatformMetadataSerializer(serializers.ModelSerializer):
    platform_name = serializers.SerializerMethodField()

    def get_platform_name(self, obj):
        return obj.platform.name

    class Meta:
        model = ConnectedPlatformMetadata
        fields = ["platform_name", "last_sync", "logged_in"]


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
