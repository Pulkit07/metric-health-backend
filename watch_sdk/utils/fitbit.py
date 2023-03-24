import logging
from watch_sdk.data_providers.fitbit import FitbitAPIClient
from celery import shared_task
from watch_sdk.models import EnabledPlatform, FitbitNotificationLog
from watch_sdk.views.fitbit import verify_fitbit_signature


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


@shared_task
def handle_fitbit_webhook(request_body, request_data, app_id, signature):
    try:
        enabled_app = EnabledPlatform.objects.get(
            user_app_id=app_id, platform__name="fitbit"
        )
    except EnabledPlatform.DoesNotExist:
        logger.error(f"fitbit webhook received for non-enabled app {app_id}")
        return

    if not verify_fitbit_signature(
        enabled_app.client_secret,
        request_body,
        signature,
    ):
        logger.error(f"fitbit signature verification failed for {app_id}")
        return

    total = 0
    for entry in request_data:
        total += 1
        FitbitNotificationLog.objects.create(
            collection_type=entry["collectionType"],
            date=entry["date"],
            owner_id=entry["ownerId"],
            owner_type=entry["ownerType"],
            subscription_id=entry["subscriptionId"],
        )

    logger.info(f"Received {total} notifications from fitbit")
