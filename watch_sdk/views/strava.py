from watch_sdk.data_providers.strava import StravaAPIClient
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    StravaWebhookLog,
    UserApp,
    WatchConnection,
)
from watch_sdk.permissions import AdminPermission
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import generics


class StravaWebhook(generics.GenericAPIView):
    def get(self, request, pk):
        mode = request.query_params.get("hub.mode")
        challenge = request.query_params.get("hub.challenge")
        verify_token = request.query_params.get("hub.verify_token")
        try:
            user_app = UserApp.objects.get(id=pk)
        except Exception:
            return Response({"error": "no user app found for given id"}, status=404)

        enabled_platform = EnabledPlatform.objects.get(
            platform__name="strava", user_app=user_app
        )
        webhook_token = enabled_platform.webhook_verify_token
        if mode == "subscribe" and verify_token == webhook_token:
            return Response(
                {"hub.challenge": challenge},
                status=200,
                content_type="application/json",
            )
        return Response(status=404)

    def post(self, request, pk):
        data = request.json()
        # if data.get("aspect_type") != "create":
        #     # We ignore all other events except create for now
        #     # TODO: we might be ignoring app deauthorization events too here
        #     return Response(status=200)

        # if data.get("object_type") != "activity":
        #     # We only care about activity events
        #     return Response(status=200)

        connected_platform = ConnectedPlatformMetadata.objects.get(
            platform__name="strava",
            email=data["owner_id"],
        )

        # TODO: handle this object ID and get the relevant activity using Strava's REST API
        object_id = data["object_id"]

        StravaWebhookLog.objects.create(
            object_id=object_id,
            object_type=data["object_type"],
            aspect_type=data["aspect_type"],
            subscription_id=data["subscription_id"],
            connected_platform=connected_platform,
            updates=data["updates"],
        )

        return Response(status=200)


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
