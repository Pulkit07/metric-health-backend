import base64
import collections
from datetime import datetime
import hashlib
import hmac
import json
import uuid

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, views, generics
from watch_sdk.data_providers.fitbit import FitbitAPIClient

from watch_sdk.data_providers.google_fit import GoogleFitConnection
from watch_sdk.data_providers.strava import StravaAPIClient
from watch_sdk.permissions import (
    AdminPermission,
    FirebaseAuthPermission,
    ValidKeyPermission,
)
from .models import (
    ConnectedPlatformMetadata,
    DataType,
    EnabledPlatform,
    FitbitNotificationLog,
    Platform,
    TestWebhookData,
    User,
    UserApp,
    WatchConnection,
)
from .serializers import (
    DataTypeSerializer,
    FitbitNotificationLogSerializer,
    PlatformBasedWatchConnection,
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
def upload_health_data_using_json_file(request):
    key = request.query_params.get("key")
    user_uuid = request.query_params.get("user_uuid")
    app = UserApp.objects.get(key=key)

    try:
        connection = WatchConnection.objects.get(app=app, user_uuid=user_uuid)
    except:
        return Response({"error": "No connection exists for this user"}, status=400)

    print(f"Health data received for {user_uuid} using a json file of app {app}")
    fitness_data = collections.defaultdict(list)
    # read over a json file passed with the request and build fitness_data
    data = request.FILES["data"].read()
    data = json.loads(data)
    total = 0
    enabled_datatypes = app.enabled_data_types.all()
    for enabled in enabled_datatypes:
        data_type = apple_healthkit.DB_DATA_TYPE_KEY_MAP.get(enabled.name)
        if not data.get(data_type):
            continue
        key, dclass = apple_healthkit.DATATYPE_NAME_CLASS_MAP.get(
            data_type, (None, None)
        )
        if not key or not dclass:
            continue
        values = data[data_type]
        for d in values:
            total += 1
            value = d["value"]
            start_time = d["date_from"]
            end_time = d["date_to"]
            fitness_data[key].append(
                dclass(
                    value=value,
                    start_time=start_time,
                    end_time=end_time,
                    source="apple_healthkit",
                    source_device=d.get("source_name"),
                ).to_dict()
            )
    print(f"Total data points received: {total}")
    if app.webhook_url:
        if fitness_data:
            print(
                f"sending {len(fitness_data)} data points to webhook from apple healthkit for {user_uuid}"
            )
            utils.send_data_to_webhook(
                fitness_data, app.webhook_url, connection.user_uuid
            )
    else:
        print("No webhook url found, skipping")
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


class DataTypeViewSet(viewsets.ModelViewSet):
    queryset = DataType.objects.all()
    serializer_class = DataTypeSerializer
    permission_classes = [AdminPermission]


# CRUD view for webhook data (for testing purpose only)
class WebhookDataViewSet(viewsets.ModelViewSet):
    queryset = TestWebhookData.objects.all()
    serializer_class = TestWebhookDataSerializer
    filterset_fields = ["uuid"]


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
                    print(
                        f"Duplicate key {key} for {uuid} with value {points['value']}"
                    )
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
        print(f"total data points for {uuid} : {len(hour_wise_map)}")
        for key, value in hour_wise_map.items():
            print(f"{key} : {value}")

        print("\n\n")

    return Response({"success": True}, status=200)


def verify_fitbit_signature(client_secret, request_body, signature):
    signing_key = client_secret + "&"
    encoded_body = base64.b64encode(
        hmac.new(
            signing_key.encode("utf-8"),
            request_body.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    )
    return encoded_body.decode("utf-8") == signature


class FitbitWebhook(generics.GenericAPIView):
    def get(self, request):
        if (
            request.query_params.get("verify")
            == "8120a0818957ced239318eb30cd2ac10e0ba12749b431972d7da036a0069ead9"
        ):
            return Response(status=204)
        return Response(status=404)

    def post(self, request):
        app_id = request.query_params.get("app_id")
        try:
            app = UserApp.objects.get(id=app_id)
        except Exception:
            # TODO: log this
            return Response(status=404)

        try:
            enabled_app = EnabledPlatform.objects.get(
                platform__name="fitbit", user_app=app
            )
        except EnabledPlatform.DoesNotExist:
            print("No enabled app found")
            return Response(status=404)
        data = request.data
        if not verify_fitbit_signature(
            enabled_app.client_secret,
            request.body,
            request.headers["X-Fitbit-Signature"],
        ):
            print("fitbit signature verification failed")
            return Response(status=404)
        total = 0
        for entry in request.data:
            total += 1
            FitbitNotificationLog.objects.create(
                collection_type=entry["collectionType"],
                date=entry["date"],
                owner_id=entry["ownerId"],
                owner_type=entry["ownerType"],
                subscription_id=entry["subscriptionId"],
            )

        print(f"Received {total} notifications from fitbit")
        return Response(status=204)


class FitbitNotificationLogViewSet(viewsets.ModelViewSet):
    queryset = FitbitNotificationLog.objects.all()
    serializer_class = FitbitNotificationLogSerializer
    permission_classes = [AdminPermission]


@api_view(["GET"])
@permission_classes([AdminPermission])
def test_fitbit_integration(request):
    apps = EnabledPlatform.objects.filter(platform__name="fitbit").values_list(
        "user_app", flat=True
    )
    for app_id in apps:
        app = UserApp.objects.get(id=app_id)
        connections = WatchConnection.objects.filter(app=app)
        for connection in connections:
            try:
                connected_platform = ConnectedPlatformMetadata.objects.get(
                    platform__name="fitbit",
                    connection=connection,
                )
            except Exception:
                continue

            with FitbitAPIClient(app, connected_platform, connection.user_uuid) as fbc:
                pass

    return Response({"success": True}, status=200)


@api_view(["POST"])
@permission_classes([AdminPermission])
def strava_cron_job(request):
    apps = EnabledPlatform.objects.filter(platform__name="strava").values_list(
        "user_app", flat=True
    )
    for app_id in apps:
        app = UserApp.objects.get(id=app_id)
        connections = WatchConnection.objects.filter(app=app)
        for connection in connections:
            try:
                connected_platform = ConnectedPlatformMetadata.objects.get(
                    platform__name="strava",
                    connection=connection,
                    logged_in=True,
                )
            except Exception:
                continue

            with StravaAPIClient(app, connected_platform, connection.user_uuid) as sac:
                sac.get_activities_since_last_sync()

    return Response({"success": True}, status=200)
