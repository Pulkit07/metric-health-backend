from django.db import models
from django.contrib.postgres.fields import ArrayField

from core.models import BaseModel


class User(BaseModel):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    phone = models.CharField(max_length=100, blank=True, null=True, unique=True)
    company_name = models.CharField(max_length=400, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)


# object for refering various platforms that we support
class Platform(BaseModel):
    # google fit, apple healthkit, strava etc.
    name = models.CharField(max_length=100, unique=True)


class DataType(BaseModel):
    name = models.CharField(max_length=200, unique=True)


class EnabledPlatform(BaseModel):
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    platform_app_id = models.CharField(max_length=200, null=True, blank=True)
    platform_app_secret = models.CharField(max_length=400, null=True, blank=True)

    @property
    def name(self):
        return self.platform.name


# a basic model for apps that user will create
class UserApp(BaseModel):
    name = models.CharField(max_length=100)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    play_store_url = models.CharField(
        max_length=100, blank=True, null=True, unique=True
    )
    app_store_url = models.CharField(max_length=100, blank=True, null=True, unique=True)
    website = models.CharField(max_length=100, blank=True, null=True)
    webhook_url = models.CharField(max_length=600, blank=True, null=True)
    key = models.CharField(max_length=100, blank=True, null=True, unique=True)
    enabled_platforms = models.ManyToManyField(EnabledPlatform, blank=True)
    payment_plan = models.CharField(
        max_length=100,
        choices=(
            ("free", "free"),
            ("startup", "startup"),
            ("business", "business"),
            ("enterprise", "enterprise"),
        ),
        default="free",
    )
    enabled_data_types = models.ManyToManyField(DataType, blank=True)


class ConnectedPlatformMetadata(BaseModel):
    platform = models.ForeignKey(Platform, on_delete=models.CASCADE)
    refresh_token = models.CharField(max_length=200, blank=True, null=True)
    last_sync = models.DateTimeField(blank=True, null=True)
    email = models.CharField(max_length=400, blank=True, null=True)
    # to track whether the refresh token is valid or not
    logged_in = models.BooleanField(default=True)
    last_modified_for_data_types = models.JSONField(blank=True, null=True)
    # useful when syncing is done from local device and hence the connection
    # depends on which device the user is checking from
    # One good example is iOS
    connected_device_uuids = ArrayField(
        models.CharField(max_length=200), blank=True, null=True
    )

    def mark_logout(self):
        self.logged_in = False
        self.save()


class WatchConnection(BaseModel):
    app = models.ForeignKey(UserApp, on_delete=models.CASCADE)
    user_uuid = models.CharField(max_length=200)
    connected_platforms = models.ManyToManyField(ConnectedPlatformMetadata, blank=True)


class FitnessData(BaseModel):
    app = models.ForeignKey(UserApp, on_delete=models.CASCADE)
    connection = models.ForeignKey(WatchConnection, on_delete=models.CASCADE, null=True)
    data = models.JSONField()
    record_start_time = models.DateTimeField()
    record_end_time = models.DateTimeField()
    data_source = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        choices=(
            ("google_fit", "google_fit"),
            ("api", "api"),
            ("sdk_healthkit", "sdk_healthkit"),
        ),
    )


class TestWebhookData(BaseModel):
    data = models.JSONField()
    uuid = models.CharField(max_length=100, blank=True, null=True)
