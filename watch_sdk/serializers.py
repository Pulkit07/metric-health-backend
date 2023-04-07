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


class DataTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataType
        fields = ["name", "id"]


class EnabledPlatformSerializer(serializers.ModelSerializer):
    platform_name = serializers.SerializerMethodField()

    def get_platform_name(self, obj):
        return obj.platform.name

    class Meta:
        model = EnabledPlatform
        fields = [
            "platform_name",
            "platform_app_id",
            "id",
            "platform_app_secret",
            "enabled_scopes",
        ]


class UserAppSerializer(serializers.ModelSerializer):
    enabled_platforms = serializers.SerializerMethodField()
    enabled_data_types = DataTypeSerializer(many=True, read_only=True)

    def get_enabled_platforms(self, obj):
        enabled_platforms = EnabledPlatform.objects.filter(user_app=obj)
        return EnabledPlatformSerializer(enabled_platforms, many=True).data

    class Meta:
        model = UserApp
        fields = "__all__"


class ConnectedPlatformMetadataSerializer(serializers.ModelSerializer):
    platform_name = serializers.SerializerMethodField()

    def get_platform_name(self, obj):
        return obj.platform.name

    class Meta:
        model = ConnectedPlatformMetadata
        fields = ["platform_name", "last_sync", "logged_in", "connected_device_uuids"]


class WatchConnectionSerializer(serializers.ModelSerializer):
    connected_platforms = serializers.SerializerMethodField()

    def get_connected_platforms(self, obj):
        connected_platforms = ConnectedPlatformMetadata.objects.filter(connection=obj)
        return ConnectedPlatformMetadataSerializer(connected_platforms, many=True).data

    class Meta:
        model = WatchConnection
        fields = "__all__"


class PlatformBasedWatchConnection(serializers.ModelSerializer):
    def to_representation(self, instance):
        data = super().to_representation(instance)
        app = instance.app
        data["connections"] = {}
        enabled_platforms = EnabledPlatform.objects.filter(user_app=app).values_list(
            "platform__name", flat=True
        )
        platform_connections = ConnectedPlatformMetadata.objects.filter(
            connection=instance,
        )
        processed = set()
        for platform_connection in platform_connections:
            if platform_connection.platform.name in enabled_platforms:
                data["connections"][
                    platform_connection.platform.name
                ] = ConnectedPlatformMetadataSerializer(platform_connection).data
                processed.add(platform_connection.platform.name)

        for platform in enabled_platforms:
            if platform not in processed:
                data["connections"][platform] = None

        return data

    class Meta:
        model = WatchConnection
        fields = ["user_uuid"]


class TestWebhookDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestWebhookData
        fields = "__all__"


class FitbitNotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FitbitNotificationLog
        fields = "__all__"


class DebugWebhookLogsSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebugWebhookLogs
        fields = "__all__"
