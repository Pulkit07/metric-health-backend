from django.db.models.signals import post_save
from django.dispatch import receiver


from .models import EnabledPlatform, Platform, User, UserApp
from django.core.mail import mail_admins
from watch_sdk.data_providers.fitbit import FitbitAPIClient

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

@receiver(post_save, sender=User)
def user_task_handler(sender, instance, created, **kwargs):
    if created:
        mail_admins("New User created",f"This Email is to infrom admin that a new user is created.\n NEW USER NAME : {instance.name} \n NEW USER EMAIL : {instance.email} \n NEW USER PHONE NUMBER : {instance.phone} \n NEW USER COMPANY NAME : {instance.company_name} \n NEW USER COUNTRY : {instance.country}")

@receiver(post_save, sender=UserApp)
def userapp_task_handler(sender, instance, created, **kwargs):
    if created:
        mail_admins("New User created",f"This Email is to infrom admin that a new app is created.\n NAME : {instance.name} \n USER : {instance.user} \n PLAY STORE URL : {instance.play_store_url} \n APP STORE URL : {instance.app_store_url} \n WEBSITE : {instance.website} \n WEBHOOK URL : {instance.webhook_url} \n ENABLED PLATFORMS : {instance.enabled_platforms} \n PAYMENT PLAN : {instance.payment_plan}")


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
