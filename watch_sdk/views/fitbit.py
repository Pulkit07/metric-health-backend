import base64
import hashlib
import hmac
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


logger = logging.getLogger(__name__)


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
            logger.error("No enabled app found for fitbit with id %s", app_id)
            return Response(status=404)
        data = request.data
        if not verify_fitbit_signature(
            enabled_app.client_secret,
            request.body,
            request.headers["X-Fitbit-Signature"],
        ):
            logger.error("fitbit signature verification failed")
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

        logger.info(f"Received {total} notifications from fitbit")
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
