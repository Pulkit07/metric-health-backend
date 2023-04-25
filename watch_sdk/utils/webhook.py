import datetime
import logging
import requests
import json
from celery import shared_task

from watch_sdk.models import DebugWebhookLogs
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


def _split_data_into_chunks(fitness_data):
    chunk_size = 2000
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


def send_data_to_webhook(
    fitness_data,
    user_app,
    user_uuid,
    platform,
):
    webhook_url = user_app.webhook_url
    # TODO: we can add a check here to see if the webhook url is valid
    if not webhook_url:
        logger.warn(
            f"Webhook url is not set for app {user_app} and user {user_uuid} on platform {platform}"
        )
        return False
    chunks = _split_data_into_chunks(fitness_data)
    logger.info(
        f"got {len(chunks)} chunks to send to webhook for {user_uuid} and app {user_app} on platform {platform}"
    )
    cur_chunk = 0
    request_succeeded = True
    failure_msg = None
    status_code = None
    for chunk in chunks:
        try:
            body = json.dumps({"data": chunk, "uuid": user_uuid})
            signature = get_webhook_signature(body, user_app.key)
            response = requests.post(
                webhook_url,
                headers={
                    "Content-Type": "application/json",
                    "X-Heka-Signature": signature,
                },
                data=body,
                timeout=10,
            )
            logger.info(f"response for chunk {cur_chunk}: {response}, {webhook_url}")
            cur_chunk += 1
            if response.status_code > 202 or response.status_code < 200:
                logger.error(
                    "Error in response, status code: %s" % response.status_code
                )
                status_code = response.status_code
                request_succeeded = False
                failure_msg = str(response)
        except Exception as e:
            logger.error("Error while sending data to webhook: %s" % e)
            request_succeeded = False
            failure_msg = str(e)

        _update_failure_count_for_webhook(user_app, request_succeeded)

        if request_succeeded:
            if user_app.debug_store_webhook_logs:
                store_webhook_log.delay(user_app.id, user_uuid, chunk)
        else:
            # TODO: we should store the current and remaining chunks here

            # Commenting out since we are sending webhook disable emails after
            # 5 consecutive failures. Also this was very noisy.
            #
            # current_time_in_ist = (
            #     datetime.datetime.now()
            #     .astimezone(tz=ZoneInfo("Asia/Kolkata"))
            #     .strftime("%Y-%m-%d %H:%M:%S")
            # )
            #
            # send_email_on_webhook_error.delay(
            #     user_app.id,
            #     platform,
            #     user_uuid,
            #     failure_msg,
            #     status_code,
            #     current_time_in_ist,
            # )
            break

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
