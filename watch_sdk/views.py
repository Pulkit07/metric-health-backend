import datetime
import json
import uuid
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework import viewsets, views, generics

from watch_sdk.google_fit import GoogleFitConnection
from watch_sdk.permissions import FirebaseAuthPermission, ValidKeyPermission
from .models import FitnessData, User, UserApp, WatchConnection
from .serializers import (
    FitnessDataSerializer,
    UserAppSerializer,
    UserSerializer,
    WatchConnectionSerializer,
)
from . import utils


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

    data = json.loads(request.data)
    FitnessData.objects.create(
        app=app,
        data=data,
        connection=connection,
        record_start_time=datetime.datetime.now(),
        record_end_time=datetime.datetime.now(),
        data_source=request.query_params.get("data_source") or "api",
    )
    print(f"Health data received for {user_uuid}: {data}")
    return Response({"success": True}, status=200)


# To be called from firebase function for now, should be removed in future
@api_view(["POST"])
def sync_from_google_fit(request):
    """
    Helper function to sync data from google fit

    The API will be hit by a cron job
    """
    utils.google_fit_cron()
    return Response({"success": True}, status=200)


class WatchConnectionListCreateView(generics.ListCreateAPIView):
    queryset = WatchConnection.objects.all()
    serializer_class = WatchConnectionSerializer
    permission_classes = [ValidKeyPermission]

    def get(self, request, format=None):
        key = request.query_params.get("key")
        user_uuid = request.query_params.get("user_uuid")
        app = UserApp.objects.get(key=key)
        connection = self.queryset.filter(app=app, user_uuid=user_uuid)
        if connection.exists():
            return Response(
                {
                    "success": True,
                    "data": WatchConnectionSerializer(connection.first()).data,
                },
                status=200,
            )
        return Response({"success": False}, status=404)

    def post(self, request, *args, **kwargs):
        key = request.query_params.get("key")
        user_uuid = request.query_params.get("user_uuid")
        platform = request.query_params.get("platform")

        if not platform in ["android", "ios"]:
            return Response({"error": "Invalid platform"}, status=400)

        google_fit_refresh_token = None
        if platform == "android":
            google_fit_refresh_token = request.data.get("google_fit_refresh_token")
            if not google_fit_refresh_token:
                return Response(
                    {"error": "google_fit_refresh_token required for android platform"},
                    status=400,
                )

        app = UserApp.objects.get(key=key)

        if WatchConnection.objects.filter(app=app, user_uuid=user_uuid).exists():
            return Response(
                {"error": "A connection with this user already exists"}, status=400
            )

        obj = WatchConnection.objects.create(
            app=app,
            user_uuid=user_uuid,
            platform=platform,
            google_fit_refresh_token=google_fit_refresh_token,
            logged_in=True,
        )
        return Response(
            {"success": True, "data": WatchConnectionSerializer(obj).data}, status=200
        )


class WatchConnectionUpdateView(generics.UpdateAPIView):
    queryset = WatchConnection.objects.all()
    serializer_class = WatchConnectionSerializer


# CRUD view for User model
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filterset_fields = ["email"]


# CRUD view for UserApp model
class UserAppViewSet(viewsets.ModelViewSet):
    queryset = UserApp.objects.all()
    serializer_class = UserAppSerializer
    filterset_fields = ["user", "key"]


# CRUD view for fitness data (for testing purpose only)
class FitnessDataViewSet(viewsets.ModelViewSet):
    queryset = FitnessData.objects.all()
    serializer_class = FitnessDataSerializer
    filterset_fields = ["app", "connection", "data_source"]


@api_view(["GET"])
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
