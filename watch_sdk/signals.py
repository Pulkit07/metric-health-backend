from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import EnabledPlatform, Platform
from .models import User,UserApp
from django.core.mail import mail_admins

@receiver(post_save, sender="watch_sdk.UserApp")
def enable_basic_platforms(sender, instance, created, **kwargs):
    if not created:
        return
    google_fit = EnabledPlatform(
        platform=Platform.objects.get(name="google_fit"),
    )
    google_fit.save()
    apple_healthkit = EnabledPlatform(
        platform=Platform.objects.get(name="apple_healthkit"),
    )
    apple_healthkit.save()
    instance.enabled_platforms.add(google_fit)
    instance.enabled_platforms.add(apple_healthkit)
    instance.save()


@receiver(post_save, sender="watch_sdk.UserApp")
def enable_basic_data_types(sender, instance, created, **kwargs):
    if not created:
        return
    from watch_sdk.models import DataType

    steps = DataType.objects.get(name="steps")
    distance = DataType.objects.get(name="distance")
    calories = DataType.objects.get(name="calories")
    instance.enabled_data_types.add(steps)
    instance.enabled_data_types.add(distance)
    instance.enabled_data_types.add(calories)
    instance.save()

def user_task_handler(sender,instance,**kwargs):
    mail_admins("New User created",f"This Email is to infrom admin that a new user is created.\n NEW USER NAME : {instance.name} \n NEW USER EMAIL : {instance.email} \n NEW USER PHONE NUMBER : {instance.phone} \n NEW USER COMPANY NAME : {instance.company_name} \n NEW USER COUNTRY : {instance.country}")
post_save.connect(user_task_handler,sender=User)

def userapp_task_handler(sender,instance,**kwargs):
    mail_admins("New User created",f"This Email is to infrom admin that a new app is created.\n NAME : {instance.name} \n USER : {instance.user} \n PLAY STORE URL : {instance.play_store_url} \n APP STORE URL : {instance.app_store_url} \n WEBSITE : {instance.website} \n WEBHOOK URL : {instance.webhook_url} \n ENABLED PLATFORMS : {instance.enabled_platforms} \n PAYMENT PLAN : {instance.payment_plan}")
post_save.connect(userapp_task_handler,sender=UserApp)


# @receiver(post_save, sender="watch_sdk.ConnectedPlatformMetadata")
# def fitbit_subscription_update(sender, instance, created, **kwargs):
#     if instance.platform.name != "fitbit":
#         return
#     import pdb

#     pdb.set_trace()
#     if created:
#         try:
#             connection = WatchConnection.objects.get(connected_platforms=instance)
#         except WatchConnection.DoesNotExist:
#             return
#         # create a fitbit subscription
#         with FitbitAPIClient(connection.app, instance, connection.user_uuid) as fac:
#             fac.create_subscription()
#     else:
#         if instance.__original_copy is None:
#             return
#         before = instance.__original_copy
#         after = instance

#         if before.logged_in != after.logged_in:
#             if after.logged_in:
#                 # create a fitbit subscription
#                 try:
#                     connection = WatchConnection.objects.get(
#                         connected_platforms=instance
#                     )
#                 except WatchConnection.DoesNotExist:
#                     return
#                 with FitbitAPIClient(
#                     connection.app, instance, connection.user_uuid
#                 ) as fac:
#                     fac.create_subscription()
#             else:
#                 # delete the fitbit subscription
#                 try:
#                     connection = WatchConnection.objects.get(
#                         connected_platforms=instance
#                     )
#                 except WatchConnection.DoesNotExist:
#                     return
#                 with FitbitAPIClient(
#                     connection.app, instance, connection.user_uuid
#                 ) as fac:
#                     fac.delete_subscription()
