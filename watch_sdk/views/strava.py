from watch_sdk.data_providers.strava import StravaAPIClient
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    StravaWebhookLog,
    UserApp,
    WatchConnection,
)
from watch_sdk.permissions import AdminPermission
import watch_sdk.utils.strava as strava_utils
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import generics


class StravaWebhook(generics.GenericAPIView):
    def get(self, request, pk):
        try:
            enabled_platform = EnabledPlatform.objects.get(
                platform__name="strava", user_app_id=pk
            )
        except Exception:
            return Response({"error": "no user app found for given id"}, status=404)

        if (
            request.query_params.get("hub.mode") == "subscribe"
            and request.query_params.get("hub.verify_token")
            == enabled_platform.webhook_verify_token
        ):
            return Response(
                {"hub.challenge": request.query_params.get("hub.challenge")},
                status=200,
                content_type="application/json",
            )
        return Response(status=404)

    def post(self, request, pk):
        strava_utils.handle_strava_webhook.delay(request.data, pk)
        return Response(status=200)


@api_view(["POST"])
@permission_classes([AdminPermission])
def debug_test_strava(request):
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
                sac._last_sync = 0
                sac._update_last_sync = False
                acts = sac.get_activities_since_last_sync()
                for key, value in acts.items():
                    print("key: ", key)
                    for val in value:
                        print(val)
                    print("")

    return Response({"success": True}, status=200)
