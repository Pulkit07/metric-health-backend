from django.db.models.signals import post_save
from django.dispatch import receiver

from watch_sdk.data_providers.fitbit import FitbitAPIClient

from .models import EnabledPlatform, Platform


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


# TODO: this is not correctly working on reconnect
@receiver(post_save, sender="watch_sdk.ConnectedPlatformMetadata")
def fitbit_subscription_update(sender, instance, created, **kwargs):
    if instance.platform.name != "fitbit":
        return
    connection = instance.connection
    if created:
        # create a fitbit subscription
        with FitbitAPIClient(connection.app, instance, connection.user_uuid) as fac:
            fac.create_subscription()
    else:
        if getattr(instance, "_ConnectedPlatformMetadata__original_copy", None) is None:
            return
        before = instance.original_copy
        after = instance
        if before.logged_in == after.logged_in:
            return

        if after.logged_in:
            # create a fitbit subscription
            with FitbitAPIClient(connection.app, instance, connection.user_uuid) as fac:
                fac.create_subscription()
        else:
            # delete the fitbit subscription
            with FitbitAPIClient(connection.app, before, connection.user_uuid) as fac:
                fac.delete_subscription()
            pass
