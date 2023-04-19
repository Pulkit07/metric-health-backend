import logging
from watch_sdk import utils
from watch_sdk.data_providers.google_fit import GoogleFitConnection
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    UserApp,
    WatchConnection,
)

from watch_sdk.permissions import AdminPermission


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
@permission_classes([AdminPermission])
def test_google_sync(request):
    apps = EnabledPlatform.objects.filter(platform__name="google_fit").values_list(
        "user_app", flat=True
    )
    google_fit_connections = ConnectedPlatformMetadata.objects.filter(
        platform__name="google_fit",
        logged_in=True,
        connection__app__in=UserApp.objects.filter(id=40),
        connection__app__webhook_url__isnull=False,
    )
    for connection in google_fit_connections:
        logging.info(f"\n\nSyncing for {connection.connection.user_uuid}")
        with GoogleFitConnection(connection.connection.app, connection) as gfc:
            gfc.test_sync()

    return Response({"success": True}, status=200)
