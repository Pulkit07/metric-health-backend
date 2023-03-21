import hashlib
import logging
from celery import shared_task
from watch_sdk.data_providers.strava import (
    create_strava_subscription,
    delete_strava_subscription,
)
from watch_sdk.models import ConnectedPlatformMetadata, EnabledPlatform, UserApp
from watch_sdk.utils.fitbit import on_fitbit_connect, on_fitbit_disconnect
from watch_sdk.utils import google_fit as google_fit_utils

logger = logging.getLogger(__name__)


def get_hash(data):
    return hashlib.sha256(str(data).encode("utf-8")).hexdigest()


@shared_task
def on_connection_create(connected_platform_id):
    connected_platform = ConnectedPlatformMetadata.objects.get(id=connected_platform_id)
    if connected_platform.platform.name == "fitbit":
        on_fitbit_connect(connected_platform)
    elif connected_platform.platform.name == "google_fit":
        google_fit_utils.trigger_sync_on_connect(connected_platform)


@shared_task
def on_connection_disconnect(connected_platform_id, refresh_token):
    """
    Refresh token is explicitly passed in because disconnect will set it as null
    """
    connected_platform = ConnectedPlatformMetadata.objects.get(id=connected_platform_id)
    if connected_platform.platform.name == "fitbit":
        on_fitbit_disconnect(connected_platform, refresh_token)


@shared_task
def on_connection_reconnect(connected_platform_id):
    connected_platform = ConnectedPlatformMetadata.objects.get(id=connected_platform_id)
    if connected_platform.platform.name == "fitbit":
        on_fitbit_connect(connected_platform)
    elif connected_platform.platform.name == "google_fit":
        google_fit_utils.trigger_sync_on_connect(connected_platform)


@shared_task
def on_platform_enable(app_id, platform_name):
    app = UserApp.objects.get(id=app_id)
    enabled_platform = EnabledPlatform.objects.get(
        user_app=app, platform__name=platform_name
    )
    if platform_name == "strava":
        logger.info("creating strava subscription")
        create_strava_subscription(app)


@shared_task
def on_platform_disable(app_id, platform_name):
    app = UserApp.objects.get(id=app_id)
    enabled_platform = EnabledPlatform.objects.get(
        user_app=app, platform__name=platform_name
    )
    if platform_name == "strava":
        logger.info("deleting strava subscription")
        delete_strava_subscription(app)
    enabled_platform.delete()
