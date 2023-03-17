import hashlib
import logging
from celery import shared_task
from watch_sdk.data_providers.fitbit import FitbitAPIClient
from watch_sdk.models import ConnectedPlatformMetadata

logger = logging.getLogger(__name__)


def get_hash(data):
    return hashlib.sha256(str(data).encode("utf-8")).hexdigest()


@shared_task
def on_connection_create(connected_platform_id):
    connected_platform = ConnectedPlatformMetadata.objects.get(id=connected_platform_id)
    if connected_platform.platform == "fitbit":
        on_fitbit_connect(connected_platform)


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


def on_fitbit_connect(connected_platform):
    # TODO: get users old data too
    with FitbitAPIClient(
        connected_platform.connection.app,
        connected_platform,
        connected_platform.connection.user_uuid,
    ) as fac:
        fac.create_subscription()


def on_fitbit_disconnect(connected_platform, refresh_token):
    with FitbitAPIClient(
        connected_platform.connection.app,
        connected_platform,
        connected_platform.connection.user_uuid,
        refresh_token=refresh_token,
    ) as fac:
        fac.delete_subscription()
