from django.db import models

from core.models import BaseModel


class User(BaseModel):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=100, unique=True)
    phone = models.CharField(max_length=100, blank=True, null=True, unique=True)
    company_name = models.CharField(max_length=400, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)


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
    key = models.CharField(max_length=100, blank=True, null=True)
    google_auth_client_id = models.CharField(max_length=200, blank=True, null=True)


class WatchConnection(BaseModel):
    app = models.ForeignKey(UserApp, on_delete=models.CASCADE)
    user_uuid = models.CharField(max_length=200)
    # TODO: this in future should be google fit, apple health, strava, fitbit, oura, etc
    platform = models.CharField(
        max_length=100, choices=(("android", "android"), ("ios", "ios"))
    )

    # only when platform is android
    google_fit_refresh_token = models.CharField(max_length=200, blank=True, null=True)

    # last sync time
    last_sync = models.DateTimeField(blank=True, null=True)


class FitnessData(BaseModel):
    app = models.ForeignKey(UserApp, on_delete=models.CASCADE)
    connection = models.ForeignKey(WatchConnection, on_delete=models.CASCADE, null=True)
    data = models.JSONField()
    record_start_time = models.DateTimeField()
    record_end_time = models.DateTimeField()
