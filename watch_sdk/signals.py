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
def enable_basic_platforms(sender, instance, created, **kwargs):
    if not created:
        return
    google_fit = EnabledPlatform(
        platform=Platform.objects.get(name="google_fit"),
        user_app=instance,
    )
    google_fit.save()
    apple_healthkit = EnabledPlatform(
        platform=Platform.objects.get(name="apple_healthkit"),
        user_app=instance,
    )
    apple_healthkit.save()
    mail_utils.send_email_on_new_app.delay(instance.id)


@receiver(post_save, sender="watch_sdk.UserApp")
def enable_basic_data_types(sender, instance, created, **kwargs):
    if not created:
        return
    from watch_sdk.models import DataType

    steps = DataType.objects.get(name="steps")
    calories = DataType.objects.get(name="calories")
    instance.enabled_data_types.add(steps)
    instance.enabled_data_types.add(calories)
    instance.save()


# TODO: handle the case when a platform is disconnected
@receiver(post_save, sender="watch_sdk.EnabledPlatform")
def strava_subscription_create(sender, instance, created, **kwargs):
    if instance.platform.name != "strava":
        return

    from watch_sdk.data_providers.strava import (
        create_strava_subscription,
        delete_strava_subscription,
    )

    if created:
        # create a strava subscription
        create_strava_subscription(instance.app)
