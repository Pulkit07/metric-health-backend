import collections
import logging
from celery import shared_task
from dateutil.parser import parse

from watch_sdk.utils import webhook
from watch_sdk.data_providers.strava import StravaAPIClient, SUPPORTED_TYPES
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    StravaWebhookLog,
    StravaWebhookSubscriptionLog,
)
from watch_sdk.utils.hash_utils import get_hash


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

    # we don't hash the whole data since it contains event_time and that changes even for duplicate
    # events
    data_hash = get_hash(
        f"{object_id}{data['object_type']}{data['aspect_type']}{data['subscription_id']}{data['owner_id']}"
    )
    if StravaWebhookSubscriptionLog.objects.filter(
        app_id=app_id,
        hash=data_hash,
    ).exists():
        logger.info("duplicate event received over strava webhook, ignoring")
        return
    else:
        StravaWebhookSubscriptionLog.objects.create(
            app_id=app_id,
            hash=data_hash,
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

    fitness_data = collections.defaultdict(list)
    if data.get("object_type") != "activity":
        # We only care about activity events
        return

    if (
        data.get("updates") is not None
        and data.get("updates").get("authorized") is False
    ):
        # If the user has revoked access, we need to disconnect the platform
        connected_platform.mark_logout()
    elif data.get("aspect_type") == "create":
        activity = None
        start_time = None

        # get the activity from strava using the object_id
        with StravaAPIClient(
            connected_platform.connection.app,
            connected_platform,
            connected_platform.connection.user_uuid,
        ) as sac:
            activity = sac.get_activity_by_id(object_id)
            if activity is None:
                return
            start_time = parse(activity["start_date"]).timestamp() * 1000
            sac._last_sync = max(sac._last_sync, start_time)

        # check if the data type is supported
        if activity["type"] not in SUPPORTED_TYPES:
            logger.info(
                f"got strava activity over webhook of unsupported type {activity['type']}"
            )
            return

        # check if the data type is enabled
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

        # Filter manual entry if not enabled
        enabled_platform = EnabledPlatform.objects.get(
            user_app=connected_platform.connection.app,
            platform__name="strava",
        )
        if activity["manual"] and not enabled_platform.sync_manual_entries:
            return

        fitness_data[activity_type].append(
            activity_class(
                source="strava",
                start_time=start_time,
                # TODO: this should be calculated based on elapsed/moving time
                end_time=start_time,
                activity_id=activity["id"],
                distance=activity["distance"],
                moving_time=activity["moving_time"],
                total_elevation_gain=activity["total_elevation_gain"],
                max_speed=activity["max_speed"],
                average_speed=activity["average_speed"],
                source_device=None,
                manual_entry=activity["manual"],
            ).to_dict()
        )

    elif data.get("aspect_type") == "delete":
        pass
    elif data.get("aspect_type") == "update":
        pass

    if not fitness_data:
        return
    # send fitness data over webhook
    webhook.send_data_to_webhook(
        fitness_data,
        connected_platform.connection.app,
        connected_platform.connection.user_uuid,
        "strava",
    )
