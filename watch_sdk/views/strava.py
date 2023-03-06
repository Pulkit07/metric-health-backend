from watch_sdk.data_providers.strava import StravaAPIClient
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    UserApp,
    WatchConnection,
)
from watch_sdk.permissions import AdminPermission
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


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
