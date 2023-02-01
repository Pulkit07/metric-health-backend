import collections
import datetime
import json
import uuid
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, views, generics

from watch_sdk.google_fit import GoogleFitConnection
from watch_sdk.permissions import (
    AdminPermission,
    FirebaseAuthPermission,
    ValidKeyPermission,
)
from .models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    FitnessData,
    Platform,
    TestWebhookData,
    User,
    UserApp,
    WatchConnection,
)
from .serializers import (
    FitnessDataSerializer,
    PlatformSerializer,
    TestWebhookDataSerializer,
    UserAppSerializer,
    UserSerializer,
    WatchConnectionSerializer,
)
from . import utils
from .constants import apple_healthkit


@api_view(["POST"])
@permission_classes([FirebaseAuthPermission])
def generate_key(request):
    app_id = request.query_params.get("app_id")
    try:
        app = UserApp.objects.get(id=app_id)
    except Exception:
        return Response({"error": "Invalid app id"}, status=400)
    key = str(uuid.uuid4())
    app.key = key
    app.save()
    return Response({"key": key}, status=200)


@api_view(["POST"])
@permission_classes([ValidKeyPermission])
def upload_health_data(request):
    key = request.query_params.get("key")
    user_uuid = request.query_params.get("user_uuid")
    app = UserApp.objects.get(key=key)

    try:
        connection = WatchConnection.objects.get(app=app, user_uuid=user_uuid)
    except:
        return Response({"error": "No connection exists for this user"}, status=400)

    data = request.data
    print(f"Health data received for {user_uuid}: {data}")
    print(type(data))
    fitness_data = collections.defaultdict(list)
    for data_type, data in data.items():
        key, dclass = apple_healthkit.DATATYPE_NAME_CLASS_MAP.get(
            data_type, (None, None)
        )
        if not key or not dclass:
            continue
        for d in data:
            value = d["value"]
            start_time = d["date_from"]
            end_time = d["date_to"]
            fitness_data[key].append(
                dclass(
                    value=value,
                    start_time=start_time,
                    end_time=end_time,
                    source="apple_healthkit",
                ).to_dict()
            )
    print(
        f"sending {len(fitness_data)} data points to webhook from apple healthkit for {user_uuid}"
    )
    utils.send_data_to_webhook(fitness_data, app.webhook_url, connection.user_uuid)
    FitnessData.objects.create(
        app=app,
        data=data,
        connection=connection,
        record_start_time=datetime.datetime.now(),
        record_end_time=datetime.datetime.now(),
        data_source=request.query_params.get("data_source") or "api",
    )
    return Response({"success": True}, status=200)


# To be called from firebase function for now, should be removed in future
@api_view(["POST"])
@permission_classes([AdminPermission])
def sync_from_google_fit(request):
    """
    Helper function to sync data from google fit

    The API will be hit by a cron job
    """
    utils.google_fit_cron()
    return Response({"success": True}, status=200)


@api_view(["GET"])
@permission_classes([ValidKeyPermission])
def watch_connection_exists(request):
    key = request.query_params.get("key")
    user_uuid = request.query_params.get("user_uuid")
    app = UserApp.objects.get(key=key)
    connection = WatchConnection.objects.filter(app=app, user_uuid=user_uuid)
    if connection.exists():
        return Response(
            {
                "success": True,
                "data": WatchConnectionSerializer(connection.first()).data,
            },
            status=200,
        )
    return Response({"success": False}, status=404)


@api_view(["POST"])
@permission_classes([ValidKeyPermission | AdminPermission])
def connect_platform_for_user(request):
    key = request.query_params.get("key")
    user_uuid = request.query_params.get("user_uuid")

    try:
        platform = Platform.objects.get(name=request.data.get("platform"))
    except Exception:
        return Response({"error": "Invalid platform"}, status=400)

    if (
        platform.name in ["android", "strava"]
        and request.data.get("platform_app_id") is None
    ):
        return Response(
            {"error": f"platform_app_id required for {platform.name}"},
            status=400,
        )

    app = UserApp.objects.get(key=key)
    if not app.enabled_platforms.filter(platform=platform).exists():
        return Response(
            {"error": f"{platform.name} is not enabled for this app"}, status=400
        )

    connections = WatchConnection.objects.filter(app=app, user_uuid=user_uuid)
    if connections.exists():
        connection: WatchConnection = connections.first()
        if connection.connected_platforms.filter(platform=platform).exists():
            return Response(
                {
                    "error": f"A connection with this user for {platform.name} already exists"
                },
                status=400,
            )

    else:
        connection = WatchConnection.objects.create(
            app=app,
            user_uuid=user_uuid,
            platform=platform,
            logged_in=True,
        )
        connection.save()

    connected_platform_metadata = ConnectedPlatformMetadata(
        platform_app_id=request.data.get("platform_app_id"),
        platform=platform,
        email=request.data.get("email"),
    )
    connected_platform_metadata.save()
    connection.connected_platforms.add(connected_platform_metadata)
    connection.save()

    return Response(
        {"success": True, "data": WatchConnectionSerializer(connection).data},
        status=200,
    )


class WatchConnectionListView(generics.ListAPIView):
    queryset = WatchConnection.objects.all()
    filterset_fields = ["app", "user_uuid", "platform", "logged_in"]
    serializer_class = WatchConnectionSerializer
    permission_classes = [ValidKeyPermission | AdminPermission]


@api_view(["POST"])
@permission_classes([FirebaseAuthPermission | AdminPermission])
def enable_platform_for_app(request):
    app = UserApp.objects.get(id=request.query_params.get("app_id"))
    try:
        platform = Platform.objects.get(name=request.data.get("platform"))
    except:
        return Response({"error": "Invalid platform"}, status=400)
    enabled_platform = EnabledPlatform(
        platform=platform, platform_app_id=request.data.get("platform_app_id")
    )
    enabled_platform.save()
    app.enabled_platforms.add(enabled_platform)
    app.save()
    return Response({"success": True}, status=200)


class WatchConnectionUpdateView(generics.RetrieveUpdateDestroyAPIView):
    queryset = WatchConnection.objects.all()
    serializer_class = WatchConnectionSerializer
    permission_classes = [ValidKeyPermission | AdminPermission]


class PlatformViewSet(viewsets.ModelViewSet):
    queryset = Platform.objects.all()
    serializer_class = PlatformSerializer
    permission_classes = [AdminPermission]


# CRUD view for User model
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filterset_fields = ["email"]
    permission_classes = [FirebaseAuthPermission | AdminPermission]


class UserAppFromKeyViewSet(generics.RetrieveAPIView):
    queryset = UserApp.objects.all()
    serializer_class = UserAppSerializer
    permission_classes = [ValidKeyPermission]

    def get(self, request, format=None):
        key = request.query_params.get("key")
        app = self.queryset.get(key=key)
        return Response({"success": True, "data": UserAppSerializer(app).data})


# CRUD view for UserApp model
class UserAppViewSet(viewsets.ModelViewSet):
    queryset = UserApp.objects.all()
    serializer_class = UserAppSerializer
    filterset_fields = ["user"]
    permission_classes = [FirebaseAuthPermission | AdminPermission]


# CRUD view for fitness data (for testing purpose only)
class FitnessDataViewSet(viewsets.ModelViewSet):
    queryset = FitnessData.objects.all()
    serializer_class = FitnessDataSerializer
    filterset_fields = ["app", "connection", "data_source"]
    permission_classes = [AdminPermission]


# CRUD view for webhook data (for testing purpose only)
class WebhookDataViewSet(viewsets.ModelViewSet):
    queryset = TestWebhookData.objects.all()
    serializer_class = TestWebhookDataSerializer
    filterset_fields = ["uuid"]
    permission_classes = [AdminPermission]


@api_view(["GET"])
@permission_classes([AdminPermission])
def test_google_sync(request):
    connections = WatchConnection.objects.filter(
        platform="android",
        logged_in=True,
        google_fit_refresh_token__isnull=False,
    )
    for connection in connections:
        print(f"\n\nSyncing for {connection.user_uuid}")
        with GoogleFitConnection(connection.app, connection) as gfc:
            gfc.test_sync()

    return Response({"success": True}, status=200)


@api_view(["POST"])
def test_webhook_endpoint(request):
    data = request.data
    print(data)
    if not data:
        return
    TestWebhookData.objects.create(
        data=data["data"],
        uuid=data["uuid"],
    )

    return Response({"success": True}, status=200)
