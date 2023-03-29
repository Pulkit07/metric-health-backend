import collections
import logging
from celery import shared_task

from watch_sdk.utils import webhook
from watch_sdk.data_providers.strava import StravaAPIClient, SUPPORTED_TYPES
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    StravaWebhookLog,
)


logger = logging.getLogger(__name__)


def on_strava_connect(connected_platform):
    # same logic as reconnect
    on_strava_reconnect(connected_platform)


def on_strava_disconnect(connected_platform, refresh_token):
    pass


def on_strava_reconnect(connected_platform):
    fitness_data = collections.defaultdict(list)
    with StravaAPIClient(
        connected_platform.connection.app,
        connected_platform,
        connected_platform.connection.user_uuid,
    ) as sac:
        activities = sac.get_activities_since_last_sync()
        for activity_type, acts in activities.items():
            for act in acts:
                fitness_data[activity_type].append(act.to_dict())

    logger.info(f"total activities on strava sync: {len(activities)}")
    logger.info(
        f"sending strava data to webhook for {connected_platform.connection.user_uuid} and app {connected_platform.connection.app}"
    )
    webhook.send_data_to_webhook(
        fitness_data,
        connected_platform.connection.app,
        connected_platform.connection.user_uuid,
        "strava",
    )


@shared_task
def handle_strava_webhook(data, app_id):
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

    if data.get("object_type") != "activity":
        # We only care about activity events
        return

    if data.get("aspect_type") == "create":
        with StravaAPIClient(
            connected_platform.connection.app,
            connected_platform,
            connected_platform.connection.user_uuid,
        ) as sac:
            activity = sac.get_activity(object_id)
            if activity is None:
                return
            if activity["type"] not in SUPPORTED_TYPES:
                logger.info(
                    f"got strava activity over webhook of unsupported type {activity['type']}"
                )
                return
            activity_type, activity_class = SUPPORTED_TYPES[activity["type"]]
            if (
                activity_type
                not in connected_platform.connection.app.enabled_data_types.values_list(
                    "name", flat=True
                )
            ):
                logger.info(
                    f"got strava activity over webhook of disabled type {activity_type}"
                )
                return

            enabled_platform = EnabledPlatform.objects.get(
                user_app=connected_platform.connection.app,
                platform__name="strava",
            )
            # Filter manual entry if not enabled
            if activity["manual"] and not enabled_platform.sync_manual_entries:
                return

            fitness_data = collections.defaultdict(list)
            fitness_data[activity_type].append(activity_class(activity).to_dict())
            # send fitness data over webhook
            webhook.send_data_to_webhook(
                fitness_data,
                connected_platform.connection.app,
                connected_platform.connection.user_uuid,
                "strava",
            )

    elif data.get("aspect_type") == "delete":
        pass
    elif data.get("aspect_type") == "update":
        # TODO: handle app deauthorization
        pass
