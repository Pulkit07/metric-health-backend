import collections
import logging
from watch_sdk.data_providers.google_fit import GoogleFitConnection

from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    UserApp,
    WatchConnection,
)
from watch_sdk.utils.webhook import send_data_to_webhook
from watch_sdk.constants import google_fit

from celery import shared_task

logger = logging.getLogger(__name__)


def trigger_sync_on_connect(connected_platform: ConnectedPlatformMetadata):
    logger.info(
        f"Triggering google_fit sync on connect for {connected_platform.connection.user_uuid} and app {connected_platform.connection.app}"
    )
    _sync_connection(connected_platform)


@shared_task
def google_fit_cron():
    apps = EnabledPlatform.objects.filter(platform__name="google_fit").values_list(
        "user_app", flat=True
    )
    google_fit_connections = ConnectedPlatformMetadata.objects.filter(
        platform__name="google_fit",
        logged_in=True,
        connection__app__in=apps,
        connection__app__webhook_url__isnull=False,
    )
    logger.info(f"Syncing google_fit for {len(google_fit_connections)} connections")
    for connection in google_fit_connections:
        _sync_connection(connection)


def _sync_connection(google_fit_connection: ConnectedPlatformMetadata):
    connection = google_fit_connection.connection
    user_app = connection.app
    logger.info(f"Syncing google_fit for {connection.user_uuid} ({user_app.name})")
    with GoogleFitConnection(user_app, google_fit_connection) as fit_connection:
        fitness_data = collections.defaultdict(list)
        if fit_connection._access_token is None:
            logger.info(
                "Unable to get access token for connection, marking it logged out"
            )
            google_fit_connection.mark_logout()
            return
        try:
            for (
                data_type,
                data,
            ) in fit_connection.get_data_since_last_sync().items():
                data_key, dclass = google_fit.RANGE_DATA_TYPES[data_type]
                for d in data:
                    fitness_data[data_key].append(
                        dclass(
                            source="google_fit",
                            start_time=int(d.start_time) / 10**6,
                            end_time=int(d.end_time) / 10**6,
                            manual_entry=False,
                            source_device=None,
                            value=d.value,
                        ).to_dict()
                    )

            if fitness_data:
                send_data_to_webhook(
                    fitness_data,
                    user_app,
                    connection.user_uuid,
                    "google_fit",
                    fit_connection,
                )
        except Exception as e:
            logger.error(
                "Unable to sync data %s, got exception %s" % (connection.user_uuid, e),
                exc_info=True,
            )
            return
