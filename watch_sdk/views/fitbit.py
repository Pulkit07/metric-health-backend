import logging
from rest_framework import viewsets, views, generics
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from watch_sdk.data_providers.fitbit import FitbitAPIClient

from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    FitbitNotificationLog,
    UserApp,
    WatchConnection,
)
from watch_sdk.permissions import AdminPermission
from watch_sdk.serializers import FitbitNotificationLogSerializer
from watch_sdk.utils.fitbit import handle_fitbit_webhook


logger = logging.getLogger(__name__)


class FitbitWebhook(generics.GenericAPIView):
    def get(self, request):
        # TODO: this verification code should be stored on server
        # instead of being hardcoded in code
        if (
            request.query_params.get("verify")
            == "65d1c14f34150210b1b9c6edc4fec10c882f511dda41fc5e3de3e8e91cc132bc"
        ):
            return Response(status=204)
        return Response(status=404)

    def post(self, request, pk):
        try:
            UserApp.objects.get(id=pk)
        except UserApp.DoesNotExist:
            logger.error(f"Received fitbit notification for non-existent app {pk}")
            return Response(status=404)

        handle_fitbit_webhook.delay(
            request.body, request.data, pk, request.headers["X-Fitbit-Signature"]
        )
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
