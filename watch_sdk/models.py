import copy
from typing import Any
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
    user_app = models.ForeignKey("UserApp", on_delete=models.CASCADE)
    # only used for Strava as of now
    webhook_verify_token = models.CharField(max_length=200, null=True, blank=True)

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
    # Sometimes platform asks to pass in a UUID while creating a subscription
    # Fitbit is one of them.
    # This is the UUID that we will pass to the platform APIs
    # we cannot use user uuid since that can contain special characters
    platform_connection_uuid = models.CharField(max_length=200, blank=True, null=True)
    connection = models.ForeignKey("WatchConnection", on_delete=models.CASCADE)

    __original_copy = None

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__original_copy = copy.deepcopy(self)

    @property
    def original_copy(self):
        return self.__original_copy

    def mark_logout(self):
        self.logged_in = False
        self.save()


class WatchConnection(BaseModel):
    app = models.ForeignKey(UserApp, on_delete=models.CASCADE)
    user_uuid = models.CharField(max_length=200)


class TestWebhookData(BaseModel):
    data = models.JSONField()
    uuid = models.CharField(max_length=100, blank=True, null=True)


class FitbitNotificationLog(BaseModel):
    collection_type = models.CharField(max_length=100)
    date = models.DateField()
    owner_id = models.CharField(max_length=100)
    owner_type = models.CharField(max_length=100)
    subscription_id = models.CharField(max_length=100)
