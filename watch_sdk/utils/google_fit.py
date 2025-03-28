import collections
import logging
from watch_sdk.data_providers.google_fit import GoogleFitConnection

from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    UserApp,
)
from watch_sdk.utils.celery_utils import single_instance_task
from watch_sdk.utils.data_process import process_health_data
from watch_sdk.constants import google_fit

from celery import shared_task
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _get_sleep_type(val):
    if val == 1:
        return "awake"
    if val == 2:
        return "sleep"
    if val == 3:
        return "out_of_bed"
    if val == 4:
        return "light"
    if val == 5:
        return "deep"
    if val == 6:
        return "rem"

    return "unspecified"


def trigger_sync_on_connect(connected_platform: ConnectedPlatformMetadata):
    if not connected_platform.connection.app.data_storage_option in set(
        ["deny", "both"]
    ):
        return
    logger.info(
        f"Google fit sync on connect for {connected_platform.connection.user_uuid} ({connected_platform.connection.app})"
    )
    _sync_connection(connected_platform.id)
    logger.info(
        f"finished google_fit on connect for {connected_platform.connection.user_uuid}"
    )


@shared_task
@single_instance_task(timeout=60 * 10)
def google_fit_cron():
    apps = EnabledPlatform.objects.filter(platform__name="google_fit").values_list(
        "user_app", flat=True
    )
    for app in apps:
        app_object = UserApp.objects.get(id=app)
        # if webhook url is not set, we skip the app
        # if data storage option is allow, we skip this syncing
        # TODO: implement new syncing logic for allow
        if app_object.webhook_url is None or app_object.data_storage_option == "allow":
            continue
        _sync_app.delay(app)


@shared_task
def _sync_app(app_id: int):
    google_fit_connections = ConnectedPlatformMetadata.objects.filter(
        platform__name="google_fit",
        logged_in=True,
        connection__app=app_id,
    ).values_list("id", flat=True)
    connections_slices = []
    # break the connections into slices and sync them in parallel
    SLICE_LENGTH = 300
    for i in range(0, len(google_fit_connections), SLICE_LENGTH):
        connections_slices.append(google_fit_connections[i : i + SLICE_LENGTH])

    for connections_slice in connections_slices:
        _sync_connections_slice.delay(connections_slice)


@shared_task
def _sync_connections_slice(connections: list):
    for connection_id in connections:
        _sync_connection(connection_id)


def _sync_connection(google_fit_connection_id: int):
    # Multiple syncs can happen for a same connection at once because of cron job, on connect trigger
    # reconnect trigger etc.
    # We need to make sure that only one sync happens at a time for a connection to prevent deduplication
    # Hence we use a redis distributed named lock
    #
    # The timeout is set to 5 minutes, which is more than enough for a sync to complete
    # We need a timeout because sometime stale locks can be left behind due to server restarts etc.
    with cache.lock(f"google_fit_sync_{google_fit_connection_id}", timeout=60 * 5):
        # load the connection object after the lock has been acquired
        # to make sure we have the latest data
        google_fit_connection = ConnectedPlatformMetadata.objects.get(
            id=google_fit_connection_id
        )
        _perform_sync_connection(google_fit_connection)


def _perform_sync_connection(google_fit_connection: ConnectedPlatformMetadata):
    connection = google_fit_connection.connection
    user_app = connection.app
    # Double check that the webhook url is set
    if user_app.webhook_url is None:
        logger.info(
            f"Webhook url is not set for app {user_app} and user {connection.user_uuid} on platform {google_fit_connection.platform}, skipping"
        )
        return
    with GoogleFitConnection(user_app, google_fit_connection) as fit_connection:
        fitness_data = collections.defaultdict(list)
        if fit_connection._access_token is None:
            if not fit_connection._google_server_error:
                logger.info("Marking logout, failed to get access token")
                google_fit_connection.mark_logout()
            else:
                logger.info("Google server error, skipping sync")
            return
        try:
            for (
                data_type,
                data,
            ) in fit_connection.get_data_since_last_sync().items():
                data_key, dclass = google_fit.RANGE_DATA_TYPES[data_type]
                for d in data:
                    if data_key == "sleep":
                        sleep_type = _get_sleep_type(d.value)
                        start_time = int(d.start_time) / 10**6
                        end_time = int(d.end_time) / 10**6
                        fitness_data[data_key].append(
                            dclass(
                                source="google_fit",
                                start_time=start_time,
                                end_time=end_time,
                                manual_entry=d.manual_entry,
                                source_device=None,
                                value=end_time - start_time,
                                sleep_type=sleep_type,
                            ).to_dict()
                        )
                    else:
                        fitness_data[data_key].append(
                            dclass(
                                source="google_fit",
                                start_time=int(d.start_time) / 10**6,
                                end_time=int(d.end_time) / 10**6,
                                manual_entry=d.manual_entry,
                                source_device=None,
                                value=d.value,
                            ).to_dict()
                        )

            if not fitness_data:
                return

            logger.info(
                f"Sending google_fit data for {connection.user_uuid} ({user_app.name})"
            )
            process_health_data(
                fitness_data,
                connection,
                user_app,
                "google_fit",
            )
        except Exception as e:
            logger.error(
                "Unable to sync data %s, got exception %s" % (connection.user_uuid, e),
                exc_info=True,
            )
            return
