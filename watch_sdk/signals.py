from .utils import mail_utils
from django.db.models.signals import post_save
from django.dispatch import receiver

from watch_sdk.data_providers.fitbit import FitbitAPIClient

from .models import EnabledPlatform, Platform


@receiver(post_save, sender="watch_sdk.User")
def mail_on_new_user(sender, instance, created, **kwargs):
    if not created:
        return
    mail_utils.send_email_on_new_user.delay(instance.id)


@receiver(post_save, sender="watch_sdk.UserApp")
def mail_on_new_app(sender, instance, created, **kwargs):
    if not created:
        return
    mail_utils.send_email_on_new_app.delay(instance.id)
