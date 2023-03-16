import collections
from datetime import datetime
import logging
import uuid

from celery import shared_task

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, views, generics

from watch_sdk.permissions import (
    AdminPermission,
    FirebaseAuthPermission,
    ValidKeyPermission,
)
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    DataType,
    EnabledPlatform,
    Platform,
    TestWebhookData,
    User,
    UserApp,
    WatchConnection,
)
from watch_sdk.serializers import (
    DataTypeSerializer,
    PlatformBasedWatchConnection,
    PlatformSerializer,
    TestWebhookDataSerializer,
    UserAppSerializer,
    UserSerializer,
    WatchConnectionSerializer,
)

logger = logging.getLogger(__name__)


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


@api_view(["GET"])
@permission_classes([ValidKeyPermission])
def watch_connection_exists(request):
    key = request.query_params.get("key")
    user_uuid = request.query_params.get("user_uuid")
    app = UserApp.objects.get(key=key)
    connection_filter = WatchConnection.objects.filter(app=app, user_uuid=user_uuid)
    if connection_filter.exists():
        return Response(
            {
                "success": True,
                "data": PlatformBasedWatchConnection(connection_filter.first()).data,
            },
            status=200,
        )
    else:
        return Response(
            {
                "success": True,
                "data": {
                    "user_uuid": user_uuid,
                    "connections": {
                        platform.name: None
                        for platform in EnabledPlatform.objects.filter(user_app=app)
                    },
                },
            },
            status=200,
        )


@api_view(["POST"])
@permission_classes([ValidKeyPermission | AdminPermission])
def connect_platform_for_user(request):
    key = request.query_params.get("key")
    user_uuid = request.query_params.get("user_uuid")
    reconnect = request.query_params.get("reconnect", False)
    disconnect = request.query_params.get("disconnect", False)
    device_id = request.data.get("device_id")

    try:
        platform = Platform.objects.get(name=request.data.get("platform"))
    except Exception:
        return Response({"error": "Invalid platform"}, status=400)

    if platform.name == "apple_healthkit":
        if not device_id:
            return Response(
                {"error": f"device_id is required for {platform.name}"}, status=400
            )
    else:
        device_id = None
        if request.data.get("refresh_token") is None and not disconnect:
            return Response(
                {"error": f"refresh_token is required for {platform.name}"}, status=400
            )

    app = UserApp.objects.get(key=key)
    if not EnabledPlatform.objects.filter(user_app=app, platform=platform).exists():
        return Response(
            {"error": f"{platform.name} is not enabled for this app"}, status=400
        )

    # We have three cases here:
    # 1. Connection does not exist, user is first time here
    #   - Create connection and connected platform metadata
    # 2. Connection exists, but connected platform metadata does not exist
    #   - Create connected platform metadata
    # 3. Connection exists, connected platform metadata exists but reconnect is true
    #   - Update connected platform metadata
    # 4. Connection exists, connected platform metadata exists but disconnect is true
    #   - Delete connected platform metadata
    connections = WatchConnection.objects.filter(app=app, user_uuid=user_uuid)
    if connections.exists():
        connection: WatchConnection = connections.first()
        connected_platform_metadata = ConnectedPlatformMetadata.objects.filter(
            connection=connection, platform=platform
        )
        if connected_platform_metadata.exists():
            connected_platform_metadata = connected_platform_metadata.first()
            if not (reconnect or disconnect) and not (
                platform.name == "apple_healthkit"
                and device_id not in connected_platform_metadata.connected_device_uuids
            ):
                return Response(
                    {
                        "error": f"A connection with this user for {platform.name} already exists"
                    },
                    status=400,
                )
            if reconnect:
                connected_platform_metadata.refresh_token = request.data.get(
                    "refresh_token"
                )
                connected_platform_metadata.email = request.data.get("email")
                connected_platform_metadata.logged_in = True
                connected_platform_metadata.connected_device_uuids = (
                    connected_platform_metadata.connected_device_uuids or []
                ) + ([device_id] if device_id else [])
            elif disconnect:
                connected_platform_metadata.refresh_token = None
                connected_platform_metadata.email = None
                connected_platform_metadata.logged_in = False
                if (
                    device_id
                    and device_id in connected_platform_metadata.connected_device_uuids
                ):
                    connected_platform_metadata.connected_device_uuids.remove(device_id)

            connected_platform_metadata.save()
            return Response(
                {
                    "success": True,
                    "data": PlatformBasedWatchConnection(connection).data,
                },
                status=200,
            )
    else:
        connection = WatchConnection.objects.create(
            app=app,
            user_uuid=user_uuid,
        )
        connection.save()

    connected_platform_metadata = ConnectedPlatformMetadata(
        refresh_token=request.data.get("refresh_token"),
        platform=platform,
        email=request.data.get("email"),
        connected_device_uuids=[device_id] if device_id else [],
        connection=connection,
    )
    connected_platform_metadata.save()

    return Response(
        {"success": True, "data": PlatformBasedWatchConnection(connection).data},
        status=200,
    )


class WatchConnectionListView(generics.ListAPIView):
    queryset = WatchConnection.objects.all()
    # TODO: implement platform wise filtering
    filterset_fields = ["app", "user_uuid"]
    serializer_class = WatchConnectionSerializer
    permission_classes = [ValidKeyPermission | AdminPermission]


@api_view(["POST"])
@permission_classes([FirebaseAuthPermission | AdminPermission])
def enable_platform_for_app(request):
    disable = request.data.get("disable", False)
    try:
        app = UserApp.objects.get(id=request.query_params.get("app_id"))
    except:
        return Response({"error": "Invalid app id"}, status=400)
    try:
        platform = Platform.objects.get(name=request.data.get("platform"))
    except:
        return Response({"error": "Invalid platform"}, status=400)

    already_enabled = EnabledPlatform.objects.filter(user_app=app, platform=platform)
    if already_enabled.exists():
        if disable:
            already_enabled.first().delete()
            return Response(
                {"success": True, "data": UserAppSerializer(app).data}, status=200
            )
        else:
            return Response(
                {"error": f"{platform.name} is already enabled for this app"},
                status=400,
            )
    enabled_platform = EnabledPlatform(
        platform=platform,
        platform_app_id=request.data.get("platform_app_id"),
        platform_app_secret=request.data.get("platform_app_secret"),
        user_app=app,
    )
    enabled_platform.save()
    return Response({"success": True, "data": UserAppSerializer(app).data}, status=200)


@api_view(["POST"])
@permission_classes([FirebaseAuthPermission | AdminPermission])
def enable_datatype_for_app(request):
    disable_list = request.data.get("disable", [])
    enable_list = request.data.get("enable", [])
    try:
        app = UserApp.objects.get(id=request.query_params.get("app_id"))
    except:
        return Response({"error": "Invalid app id"}, status=400)

    for enable in enable_list:
        try:
            datatype = DataType.objects.get(name=enable)
        except:
            return Response({"error": f"Invalid datatype {enable}"}, status=400)
        app.enabled_data_types.add(datatype)
    for disable in disable_list:
        try:
            datatype = DataType.objects.get(name=disable)
        except:
            return Response({"error": f"Invalid datatype {disable}"}, status=400)
        app.enabled_data_types.remove(datatype)

    app.save()
    return Response({"success": True, "data": UserAppSerializer(app).data}, status=200)


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

    def update(self, request, *args, **kwargs):
        if request.data.get("google_auth_client_id") is not None:
            app = self.get_object()
            enabled_platform = EnabledPlatform.objects.filter(
                user_app=app, platform__name="google_fit"
            )
            print("we are in")
            if enabled_platform.exists():
                enabled_platform = enabled_platform.first()
                enabled_platform.platform_app_id = request.data.get(
                    "google_auth_client_id"
                )
                enabled_platform.save()
        return super().update(request, *args, **kwargs)


class DataTypeViewSet(viewsets.ModelViewSet):
    queryset = DataType.objects.all()
    serializer_class = DataTypeSerializer
    permission_classes = [AdminPermission]


# CRUD view for webhook data (for testing purpose only)
class WebhookDataViewSet(viewsets.ModelViewSet):
    queryset = TestWebhookData.objects.all()
    serializer_class = TestWebhookDataSerializer
    filterset_fields = ["uuid"]


@api_view(["POST"])
def test_webhook_endpoint(request):
    data = request.data
    if not data:
        return
    TestWebhookData.objects.create(
        data=data["data"],
        uuid=data["uuid"],
    )

    return Response({"success": True}, status=200)


@api_view(["GET"])
@permission_classes([AdminPermission])
def analyze_webhook_data(request):
    # for each uuid in TestWebhookData, let's build date wise aggregated data
    uuids = TestWebhookData.objects.values_list("uuid", flat=True).distinct()
    for uuid in uuids:
        datas = TestWebhookData.objects.filter(uuid=uuid)
        hour_wise_map = collections.defaultdict(int)
        start_end_set = set()
        for data in datas:
            for points in data.data["steps"]:
                start_time = points["start_time"] / 1000
                end_time = points["end_time"] / 1000
                key = f"{start_time}-{end_time}"
                if key in start_end_set:
                    pass
                    # logger.warn(
                    #     f"Duplicate key {key} for {uuid} with value {points['value']}"
                    # )
                else:
                    start_end_set.add(key)
                # convert start time to date and hour format
                date = datetime.fromtimestamp(start_time, tz=ZoneInfo("Asia/Kolkata"))
                end_date = datetime.fromtimestamp(end_time, tz=ZoneInfo("Asia/Kolkata"))
                start_date = datetime.strftime(date, "%Y-%m-%d %H")
                end_date = datetime.strftime(end_date, "%Y-%m-%d %H")
                # if start_date != end_date:
                #     continue
                hour_wise_map[datetime.strftime(date, "%Y-%m-%d")] += points["value"]

        # pretty print the hour wise data we have
        logger.info(f"total data points for {uuid} : {len(hour_wise_map)}")
        for key, value in hour_wise_map.items():
            logger.debug(f"{key} : {value}")

        logger.debug("\n\n")

    return Response({"success": True}, status=200)


@api_view(["GET"])
def test_celery_view(request):
    test_celery_task.delay()
    return Response({"success": True}, status=200)


@shared_task()
def test_celery_task():
    logger.info("test celery task called")
    return True
