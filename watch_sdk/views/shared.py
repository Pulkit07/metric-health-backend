import collections
from datetime import datetime
import logging
import uuid

from celery import shared_task
from watch_sdk.utils.app import get_user_app

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, views, generics
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from django.utils.decorators import method_decorator
from django.db.models import Count

import watch_sdk.utils.mixpanel as mp
from watch_sdk.permissions import (
    has_user_access_to_app,
    AdminPermission,
    AppAuthPermission,
    FirebaseAuthPermission,
    ValidKeyPermission,
)
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    DataType,
    DebugWebhookLogs,
    EnabledPlatform,
    PendingUserInvitation,
    Platform,
    TestWebhookData,
    User,
    UserApp,
    WatchConnection,
)
from watch_sdk.serializers import (
    DataTypeSerializer,
    DebugWebhookLogsSerializer,
    PendingUserInvitationSerializer,
    PlatformBasedWatchConnection,
    PlatformSerializer,
    TestWebhookDataSerializer,
    UserAppMinimalSerializer,
    UserAppSerializer,
    UserSerializer,
    WatchConnectionSerializer,
)

from watch_sdk.utils import connection as connection_utils
from watch_sdk.utils.app import get_user_from_token

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
    key = (
        request.query_params.get("key")
        if request.query_params.get("key")
        else request.META.get("HTTP_KEY")
    )
    user_uuid = request.query_params.get("user_uuid")
    app = UserApp.objects.get(key=key)
    connection_filter = WatchConnection.objects.filter(app=app, user_uuid=user_uuid)
    connection_exists = connection_filter.exists()
    mp.track_load_connection.delay(user_uuid, app.id, connection_exists)
    if connection_exists:
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
    key = (
        request.query_params.get("key")
        if request.query_params.get("key")
        else request.META.get("HTTP_KEY")
    )
    user_uuid = request.query_params.get("user_uuid")
    # we should remove this from query param as 'false' in query param will be
    # parsed as a string leading to it being treated as True
    disconnect = request.query_params.get("disconnect", False) or request.data.get(
        "disconnect", False
    )
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
    # 3. Connection exists, connected platform metadata exists but disconnect is false
    #   - Update connected platform metadata
    # 4. Connection exists, connected platform metadata exists but disconnect is true
    #   - Delete connected platform metadata
    #
    # (TODO: pulkit 26/12/23): this code is bit complex, we should refactor it based
    # on intent instead of connection exists and not
    #
    connections = WatchConnection.objects.filter(app=app, user_uuid=user_uuid)
    if connections.exists():
        connection: WatchConnection = connections.first()
        connected_platform_metadata = ConnectedPlatformMetadata.objects.filter(
            connection=connection, platform=platform
        )
        if connected_platform_metadata.exists():
            connected_platform_metadata = connected_platform_metadata.first()
            if disconnect:
                if (
                    platform.name != "apple_healthkit"
                    and connected_platform_metadata.logged_in == False
                ):
                    return Response(
                        {"error": f"User is not logged in to {platform.name}"},
                        status=400,
                    )

                connection_utils.on_connection_disconnect.delay(
                    connected_platform_metadata.id,
                    connected_platform_metadata.refresh_token,
                )
                connected_platform_metadata.refresh_token = None
                connected_platform_metadata.email = None
                connected_platform_metadata.logged_in = False
                if (
                    device_id
                    and device_id in connected_platform_metadata.connected_device_uuids
                ):
                    connected_platform_metadata.connected_device_uuids.remove(device_id)
                connected_platform_metadata.save()
            else:
                if (
                    connected_platform_metadata.logged_in == True
                    and platform.name != "apple_healthkit"
                ):
                    return Response(
                        {"error": f"User is already logged in to {platform.name}"},
                        status=400,
                    )
                connected_platform_metadata.refresh_token = request.data.get(
                    "refresh_token"
                )
                connected_platform_metadata.email = request.data.get("email")
                connected_platform_metadata.logged_in = True
                connected_platform_metadata.connected_device_uuids = (
                    connected_platform_metadata.connected_device_uuids or []
                ) + ([device_id] if device_id else [])
                connected_platform_metadata.save()
                connection_utils.on_connection_reconnect.delay(
                    connected_platform_metadata.id
                )

            return Response(
                {
                    "success": True,
                    "data": PlatformBasedWatchConnection(connection).data,
                },
                status=200,
            )
    else:
        if disconnect:
            return Response({"error": "No connection exists for this user"}, status=400)
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
    connection_utils.on_connection_create.delay(connected_platform_metadata.id)

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
    try:
        app = UserApp.objects.get(id=request.query_params.get("app_id"))
    except:
        return Response({"error": "Invalid app id"}, status=400)

    # check user's permission for the app
    user = get_user_from_token(request)
    if not has_user_access_to_app(user, app):
        return Response({"error": "Forbidden Error"}, status=403)

    for platform, data in request.data.items():
        try:
            platform = Platform.objects.get(name=platform)
        except:
            return Response({"error": "Invalid platform"}, status=400)

        enabled = data.get("enabled", False)
        already_enabled = EnabledPlatform.objects.filter(
            user_app=app, platform=platform
        )
        if already_enabled.exists() and not enabled:
            # Delete the enabled platform
            # we delete the enabled platform in a celery task post platform specific
            # disabling is done
            connection_utils.on_platform_disable.delay(
                app.id, already_enabled.first().name
            )
        elif enabled and not already_enabled.exists():
            # Create a new enabled platform
            enabled_platform = EnabledPlatform(
                platform=platform,
                platform_app_id=data.get("platform_app_id"),
                platform_app_secret=data.get("platform_app_secret"),
                user_app=app,
                sync_manual_entries=data.get("sync_manual_entries", False),
            )
            enabled_platform.save()
            connection_utils.on_platform_enable.delay(app.id, enabled_platform.name)
        elif enabled and already_enabled.exists():
            # Update an already enabled platform
            enabled_platform = already_enabled.first()
            enabled_platform.platform_app_id = data.get("platform_app_id")
            enabled_platform.platform_app_secret = data.get("platform_app_secret")
            enabled_platform.sync_manual_entries = data.get(
                "sync_manual_entries", False
            )
            enabled_platform.save()
            # TODO: should we try create a subscription here?

    return Response({"success": True}, status=200)


@api_view(["POST"])
@permission_classes([FirebaseAuthPermission | AdminPermission])
def enable_datatype_for_app(request):
    enable_list = request.data.get("enable", [])
    try:
        app = UserApp.objects.get(id=request.query_params.get("app_id"))
    except:
        return Response({"error": "Invalid app id"}, status=400)

    # check user's permission for the app
    user = get_user_from_token(request)
    if not has_user_access_to_app(user, app):
        return Response({"error": "Forbidden Error"}, status=403)

    for enable in enable_list:
        try:
            DataType.objects.get(name=enable)
        except DataType.DoesNotExist:
            return Response({"error": f"Invalid datatype {enable}"}, status=400)

    app.enabled_data_types.set(
        DataType.objects.filter(name__in=enable_list), clear=True
    )
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


@api_view(["POST"])
@permission_classes([FirebaseAuthPermission | AdminPermission])
def check_or_create_user(request):
    email = request.data.get("email")
    if not email:
        return Response({"error": "email is required"}, status=400)
    name = request.data.get("name")
    app = None
    try:
        user = User.objects.get(email=email)
        app = get_user_app(user)
    except User.DoesNotExist:
        user = User.objects.create(name=name, email=email)
        invitation = PendingUserInvitation.objects.filter(email=email)
        if invitation.exists():
            invitation = invitation.first()
            app = invitation.app
            app.access_users.add(user)
            app.save()
            invitation.delete()

    return Response(
        {
            "success": True,
            "data": {
                "user": UserSerializer(user).data,
                "app": UserAppMinimalSerializer(app).data if app else None,
            },
        },
        status=200,
    )


@api_view(["POST"])
@permission_classes([FirebaseAuthPermission | AdminPermission])
def set_webhook_url_for_app(request):
    try:
        app = UserApp.objects.get(id=request.query_params.get("app_id"))
    except:
        return Response({"error": "Invalid app id"}, status=400)

    # check user's permission for the app
    user = get_user_from_token(request)
    if not has_user_access_to_app(user, app):
        return Response({"error": "Forbidden Error"}, status=403)

    # TODO: validate webhook url
    app.webhook_url = request.data.get("webhook_url")
    app.save()
    return Response({"success": True, "data": UserAppSerializer(app).data}, status=200)


@api_view(["POST"])
@permission_classes([ValidKeyPermission])
def update_webhook_for_app(request):
    key = (
        request.query_params.get("key")
        if request.query_params.get("key")
        else request.META.get("HTTP_KEY")
    )
    try:
        app = UserApp.objects.get(key=key)
    except UserApp.DoesNotExist:
        return Response({"error": "Invalid key"}, status=400)

    app.webhook_url = request.data.get("webhook_url")
    app.save()
    return Response({"success": True}, status=200)


@api_view(["GET"])
@permission_classes([ValidKeyPermission | AdminPermission])
def check_connection_and_get_user_app(request):
    key = (
        request.query_params.get("key")
        if request.query_params.get("key")
        else request.META.get("HTTP_KEY")
    )
    if key is None:
        return Response({"error": "key is required"}, status=400)
    try:
        # TODO: this should be cached
        app = UserApp.objects.get(key=key)
    except UserApp.DoesNotExist:
        return Response({"error": "Invalid key"}, status=400)

    user_uuid = request.query_params.get("user_uuid")
    if not user_uuid:
        return Response({"error": "user_uuid is required"}, status=400)

    connection_data = None
    connection_filter = WatchConnection.objects.filter(app=app, user_uuid=user_uuid)
    connection_exists = connection_filter.exists()
    mp.track_load_connection.delay(user_uuid, app.id, connection_exists)
    if connection_exists:
        connection_data = PlatformBasedWatchConnection(connection_filter.first()).data
    else:
        connection_data = {
            "user_uuid": user_uuid,
            "connections": {
                platform.name: None
                for platform in EnabledPlatform.objects.filter(user_app=app)
            },
        }

    return Response(
        {
            "success": True,
            "data": {
                "app": UserAppSerializer(app).data,
                "connection": connection_data,
            },
        },
        status=200,
    )


class UserAppFromKeyViewSet(generics.RetrieveAPIView):
    queryset = UserApp.objects.all()
    serializer_class = UserAppSerializer
    permission_classes = [ValidKeyPermission]

    @method_decorator(cache_page(60 * 60 * 24))
    @method_decorator(
        vary_on_headers(
            "key",
        )
    )
    def get(self, request, format=None):
        key = (
            request.query_params.get("key")
            if request.query_params.get("key")
            else request.META.get("HTTP_KEY")
        )
        app = self.queryset.get(key=key)
        return Response({"success": True, "data": UserAppSerializer(app).data})


# CRUD view for UserApp model
class UserAppViewSet(viewsets.ModelViewSet):
    queryset = UserApp.objects.all()
    serializer_class = UserAppSerializer
    filterset_fields = ["user"]

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        """
        if self.action in ["create", "list"]:
            permission_classes = [FirebaseAuthPermission | AdminPermission]
        else:
            permission_classes = [AppAuthPermission | AdminPermission]
        return [permission() for permission in permission_classes]


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


class DebugWebhookLogsViewSet(viewsets.ModelViewSet):
    queryset = DebugWebhookLogs.objects.all()
    serializer_class = DebugWebhookLogsSerializer
    permission_classes = [AdminPermission]
    filterset_fields = ["uuid", "app"]


class PendingUserInvitationViewSet(viewsets.ModelViewSet):
    queryset = PendingUserInvitation.objects.all()
    serializer_class = PendingUserInvitationSerializer
    permission_classes = [FirebaseAuthPermission | AdminPermission]
    filterset_fields = ["app"]

    def create(self, request, *args, **kwargs):
        # check if the user is already invited
        if PendingUserInvitation.objects.filter(
            app=request.data.get("app"), email=request.data.get("email")
        ).exists():
            return Response(
                {"error": "User already invited"},
                status=400,
            )

        # check if the user is already a member
        if User.objects.filter(email=request.data.get("email")).exists():
            return Response(
                {"error": "User already a member"},
                status=400,
            )
        return super().create(request, *args, **kwargs)


class DashboardView(views.APIView):
    permission_classes = [FirebaseAuthPermission | AdminPermission]

    def get(self, request, pk):
        try:
            user = User.objects.get(id=pk)
        except User.DoesNotExist:
            return Response({"error": "Invalid user id"}, status=400)

        # get the app for this user
        app = get_user_app(user)

        if not app:
            return Response({"error": "App not found for this user"}, status=400)

        # get total unique watch connections for this app
        total_unique_users = WatchConnection.objects.filter(app=app).count()

        # get total number of active connections for each platform
        total_active_connections_per_platform = (
            ConnectedPlatformMetadata.objects.filter(
                connection__app=app,
                logged_in=True,
            )
            .values("platform__name")
            .annotate(total=Count("platform__name"))
        )

        # get total number of active connections
        total_active_connections = sum(
            [x["total"] for x in total_active_connections_per_platform]
        )

        total_disconnected_connections = ConnectedPlatformMetadata.objects.filter(
            connection__app=app,
            logged_in=False,
        ).count()

        return Response(
            {
                "success": True,
                "data": {
                    "app_name": app.name,
                    "total_unique_users": total_unique_users,
                    "total_active_connections": total_active_connections,
                    "total_disconnected_connections": total_disconnected_connections,
                    "total_active_connections_per_platform": total_active_connections_per_platform,
                },
            },
            status=200,
        )
