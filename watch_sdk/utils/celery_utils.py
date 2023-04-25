import functools
import logging
from django.core.cache import cache
from celery import shared_task
from watch_sdk.models import UnprocessedData
from watch_sdk.utils.webhook import send_data_to_webhook
import time

logger = logging.getLogger(__name__)


def single_instance_task(timeout):
    def task_exc(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ret_value = None
            lock_id = "celery-single-instance-" + func.__name__
            lock = cache.lock(lock_id, timeout=timeout)
            try:
                have_lock = lock.acquire(blocking=False)
                if have_lock:
                    ret_value = func(*args, **kwargs)
            finally:
                if have_lock:
                    try:
                        lock.release()
                    except Exception as e:
                        logger.info(f"error while releasing lock for {lock_id}: {e}")

            return ret_value

        return wrapper

    return task_exc


@shared_task
@single_instance_task(timeout=60 * 60)
def sync_unprocessed_data():
    logger.info(f"[CRON] Syncing unprocessed")
    synced = 0
    total = UnprocessedData.objects.count()
    for entry in list(UnprocessedData.objects.all()):
        if not entry.connection.app.webhook_url:
            continue

        success = send_data_to_webhook(
            entry.data,
            entry.connection.app,
            entry.connection.user_uuid,
            entry.platform.name,
        )

        if success:
            synced += 1
            entry.delete()

        # sleep for couple of seconds to avoid DDOSing the webhook
        time.sleep(2)

    logger.info(f"[CRON] Synced unprocessed, {synced}/{total}")
