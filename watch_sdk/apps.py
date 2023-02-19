from django.apps import AppConfig


class WatchSdkConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "watch_sdk"

    def ready(self) -> None:
        from . import signals  # noqa

        return super().ready()
