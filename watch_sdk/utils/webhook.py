import datetime
import logging
import requests
import json
from celery import shared_task

from watch_sdk.models import (
    DataSyncMetric,
    DataType,
    DebugWebhookLogs,
    Platform,
    UnprocessedData,
)
from watch_sdk.utils.hash_utils import get_webhook_signature
from watch_sdk.utils.mail_utils import (
    send_email_on_webhook_disabled,
    send_email_on_webhook_error,
)
from django.core.cache import cache

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo


FAILURE_THRESHOLD = 5
logger = logging.getLogger(__name__)


def _store_data_sync_metric(user_app, chunk, platform_name):
    for data_type, data in chunk.items():
        total = 0
        for d in data:
            total += d.get("value", 0)

        DataSyncMetric.objects.create(
            app=user_app,
            value=total,
            data_type=DataType.objects.get(name=data_type),
            platform=Platform.objects.get(name=platform_name),
        )


def _split_data_into_chunks(fitness_data):
    chunk_size = 500
    data_chunks = []
    for data_type, data in fitness_data.items():
        for i in range(0, len(data), chunk_size):
            data_chunks.append({data_type: data[i : i + chunk_size]})
    return data_chunks


def _disable_webhook_for_app(user_app):
    send_email_on_webhook_disabled(user_app.id, user_app.webhook_url)
    user_app.webhook_url = None
    user_app.save()


def _update_failure_count_for_webhook(user_app, success):
    """
    Updates a global redis cache with lock to keep track of the number of times
    a webhook has failed. If the number of failures exceeds a threshold, we
    disable the webhook for the app.
    """
    with cache.lock(f"webhook_failure_lock_{user_app.id}", timeout=10):
        if success:
            cache.set(f"webhook_failure_count_{user_app.id}", 0)
        else:
            count = cache.get(f"webhook_failure_count_{user_app.id}", 0)
            if count == FAILURE_THRESHOLD:
                _disable_webhook_for_app(user_app)
                # Reset the count since we disabled the webhook
                cache.set(f"webhook_failure_count_{user_app.id}", 0)
            else:
                cache.set(f"webhook_failure_count_{user_app.id}", count + 1)


def _save_unprocessed_data(connection, fitness_data, platform_name):
    """
    Stores the data that was not processed by the webhook due to either of following:

    * The webhook was down
    * The webhook was not set up for the app
    """
    UnprocessedData.objects.create(
        data=fitness_data,
        connection=connection,
        platform=Platform.objects.get(name=platform_name),
    )


def _post_chunk(webhook_url, chunk, user_uuid, key):
    try:
        body = json.dumps({"data": chunk, "uuid": user_uuid})
        signature = get_webhook_signature(body, key)
        response = requests.post(
            webhook_url,
            headers={
                "Content-Type": "application/json",
                "X-Heka-Signature": signature,
            },
            data=body,
            timeout=10,
        )
        if response.status_code > 202 or response.status_code < 200:
            logger.warning("[webhook fail] status code: %s" % response.status_code)
            return False
    except Exception as e:
        logger.warning("[webhook fail] error: %s" % e)
        return False

    return True


def send_data_to_webhook(
    fitness_data,
    user_app,
    platform,
    watch_connection,
):
    user_uuid = watch_connection.user_uuid
    webhook_url = user_app.webhook_url
    # TODO: we can add a check here to see if the webhook url is valid
    if not webhook_url:
        logger.info(f"Webhook url not set for {user_app} storing offline")
        _save_unprocessed_data(watch_connection, fitness_data, platform)
        return False
    chunks = _split_data_into_chunks(fitness_data)
    logger.info(f"got {len(chunks)} chunks for {user_uuid}, app {user_app}, {platform}")
    request_succeeded = True
    skip_sending_due_to_error = False
    for chunk in chunks:
        if skip_sending_due_to_error:
            _save_unprocessed_data(watch_connection, chunk, platform)
        else:
            request_succeeded = _post_chunk(webhook_url, chunk, user_uuid, user_app.key)
            _update_failure_count_for_webhook(user_app, request_succeeded)

            if request_succeeded:
                _store_data_sync_metric(user_app, chunk, platform)
                if user_app.debug_store_webhook_logs:
                    store_webhook_log.delay(user_app.id, user_uuid, chunk)
            else:
                _save_unprocessed_data(watch_connection, chunk, platform)
                # dont send future chunks if this one failed
                skip_sending_due_to_error = True

    return request_succeeded


@shared_task
def store_webhook_log(app_id, uuid, data):
    DebugWebhookLogs.objects.create(
        app_id=app_id,
        uuid=uuid,
        data=data,
    )


@shared_task
def logs_delete():
    """
    Delete webhook logs older than 2 days
    """
    DebugWebhookLogs.objects.filter(
        created_at__lt=datetime.datetime.now() - datetime.timedelta(days=2)
    ).delete()
