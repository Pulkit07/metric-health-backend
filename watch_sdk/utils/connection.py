import hashlib
import logging
from celery import shared_task
from watch_sdk.models import ConnectedPlatformMetadata
from watch_sdk.utils.fitbit import on_fitbit_connect, on_fitbit_disconnect
from watch_sdk.utils import google_fit as google_fit_utils

logger = logging.getLogger(__name__)


def get_hash(data):
    return hashlib.sha256(str(data).encode("utf-8")).hexdigest()


@shared_task
def on_connection_create(connected_platform_id):
    connected_platform = ConnectedPlatformMetadata.objects.get(id=connected_platform_id)
    if connected_platform.platform == "fitbit":
        on_fitbit_connect(connected_platform)
    elif connected_platform.platform == "google_fit":
        google_fit_utils.trigger_sync_on_connect(connected_platform)


@shared_task
def on_connection_disconnect(connected_platform_id, refresh_token):
    """
    Refresh token is explicitly passed in because disconnect will set it as null
    """
    connected_platform = ConnectedPlatformMetadata.objects.get(id=connected_platform_id)
    if connected_platform.platform == "fitbit":
        on_fitbit_disconnect(connected_platform, refresh_token)


@shared_task
def on_connection_reconnect(connected_platform_id):
    connected_platform = ConnectedPlatformMetadata.objects.get(id=connected_platform_id)
    if connected_platform.platform == "fitbit":
        on_fitbit_connect(connected_platform)
    elif connected_platform.platform == "google_fit":
        google_fit_utils.trigger_sync_on_connect(connected_platform)
