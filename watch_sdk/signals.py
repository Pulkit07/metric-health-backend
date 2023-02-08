from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import EnabledPlatform, Platform, UserApp


@receiver(post_save, sender=UserApp)
def enable_basic_platforms(sender, instance, created, **kwargs):
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
