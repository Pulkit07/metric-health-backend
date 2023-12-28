import os
from mixpanel import Mixpanel
from celery import shared_task

from watch_sdk.models import ConnectedPlatformMetadata, WatchConnection

mp = Mixpanel(os.getenv("MIXPANEL_TOKEN"))


def track_connect(connected_platform: ConnectedPlatformMetadata):
    mp.track(
        connected_platform.connection.user_uuid,
        "Connect",
        {
            "platform": connected_platform.platform.name,
            "app": connected_platform.connection.app.id,
        },
    )
    mp.people_set(
        connected_platform.connection.user_uuid,
        {
            "connected": True,
            "platform": connected_platform.platform.name,
            "app": connected_platform.connection.app.id,
            "connection_exists": True,
        },
    )


def track_disconnect(connected_platform: ConnectedPlatformMetadata):
    mp.track(
        connected_platform.connection.user_uuid,
        "Disconnect",
        {
            "platform": connected_platform.platform.name,
            "app": connected_platform.connection.app.id,
        },
    )
    mp.people_set(
        connected_platform.connection.user_uuid,
        {
            "connected": False,
            "platform": None,
        },
    )


@shared_task
def track_load_connection(user_uuid: str, app_id: int, connection_exists: bool):
    mp.people_set_once(
        user_uuid,
        {"app": app_id, "connection_exists": connection_exists},
    )
    mp.track(
        user_uuid,
        "Load Connection",
        {
            "app": app_id,
        },
    )
