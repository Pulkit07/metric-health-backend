from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import EnabledPlatform, Platform


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
    calories = DataType.objects.get(name="calories")
    instance.enabled_data_types.add(steps)
    instance.enabled_data_types.add(calories)
    instance.save()


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
