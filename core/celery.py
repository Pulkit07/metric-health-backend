import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "google-fit-data-sync": {
        "task": "watch_sdk.utils.google_fit.google_fit_cron",
        "schedule": crontab(minute="*/10"),
    },
    "webhook-logs-delete": {
        "task": "watch_sdk.utils.webhook.logs_delete",
        "schedule": crontab(hour=0, minute=0),
    },
    "sync-unprocessed-data": {
        "task": "watch_sdk.utils.celery_utils.sync_unprocessed_data",
        "schedule": crontab(hour="*/2"),
    },
}
