import datetime
import logging
import requests
import json
from celery import shared_task

from watch_sdk.models import DebugWebhookLogs
from watch_sdk.utils.mail_utils import send_email_on_webhook_error

logger = logging.getLogger(__name__)


def _split_data_into_chunks(fitness_data):
    chunk_size = 1000
    data_chunks = []
    for data_type, data in fitness_data.items():
        for i in range(0, len(data), chunk_size):
            data_chunks.append({data_type: data[i : i + chunk_size]})
    return data_chunks


def send_data_to_webhook(
    fitness_data,
    user_app,
    user_uuid,
    platform,
    fit_connection=None,
):
    webhook_url = user_app.webhook_url
    chunks = _split_data_into_chunks(fitness_data)
    logger.info("got chunks %s" % len(chunks))
    cur_chunk = 0
    request_succeeded = True
    failure_msg = None
    for chunk in chunks:
        try:
            response = requests.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                data=json.dumps({"data": chunk, "uuid": user_uuid}),
            )
            logger.info(f"response for chunk {cur_chunk}: {response}, {webhook_url}")
            cur_chunk += 1
            if response.status_code > 202 or response.status_code < 200:
                logger.error(
                    "Error in response, status code: %s" % response.status_code
                )
                request_succeeded = False
                failure_msg = str(response)
        except Exception as e:
            logger.error("Error while sending data to webhook: %s" % e)
            request_succeeded = False
            failure_msg = str(e)

        if request_succeeded:
            store_webhook_log.delay(user_app.id, user_uuid, chunk)
        else:
            if fit_connection:
                fit_connection._update_last_sync = False

            send_email_on_webhook_error.delay(
                user_app.id,
                platform,
                user_uuid,
                fitness_data,
                failure_msg,
                response.status_code,
            )
            break


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
