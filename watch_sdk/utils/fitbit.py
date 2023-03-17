import logging
from watch_sdk.data_providers.fitbit import FitbitAPIClient


logger = logging.getLogger(__name__)


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
