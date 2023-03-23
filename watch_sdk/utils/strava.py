import logging
from celery import shared_task

from watch_sdk.data_providers.strava import StravaAPIClient
from watch_sdk.models import ConnectedPlatformMetadata, StravaWebhookLog


logger = logging.getLogger(__name__)


def on_strava_connect(connected_platform):
    # same logic as reconnect
    on_strava_reconnect(connected_platform)


def on_strava_disconnect(connected_platform, refresh_token):
    pass


def on_strava_reconnect(connected_platform):
    with StravaAPIClient(
        connected_platform.connection.app,
        connected_platform,
        connected_platform.connection.user_uuid,
    ) as sac:
        activities = sac.get_activities_since_last_sync()
        # TODO: sent this activities over webhook


@shared_task
def handle_strava_webhook(data, app_id):
    # TODO: handle this object ID and get the relevant activity using Strava's REST API
    object_id = data["object_id"]
    connected_platform = ConnectedPlatformMetadata.objects.get(
        platform__name="strava",
        email=data["owner_id"],
    )
    StravaWebhookLog.objects.create(
        object_id=object_id,
        object_type=data["object_type"],
        aspect_type=data["aspect_type"],
        subscription_id=data["subscription_id"],
        connected_platform=connected_platform,
        updates=data["updates"],
    )

    assert connected_platform.connection.app.id == app_id
    # if data.get("aspect_type") != "create":
    #     # We ignore all other events except create for now
    #     # TODO: we might be ignoring app deauthorization events too here
    #     return Response(status=200)

    # if data.get("object_type") != "activity":
    #     # We only care about activity events
    #     return Response(status=200)

    # with StravaAPIClient(
    #     connected_platform.connection.app,
    #     connected_platform,
    #     connected_platform.connection.user_uuid,
    # ) as sac:
    #     pass
