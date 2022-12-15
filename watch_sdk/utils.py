import json

from watch_sdk.google_fit import GoogleFitConnection
from .models import UserApp, WatchConnection
import requests
import datetime
from zoneinfo import ZoneInfo


def google_fit_cron():
    apps = (
        WatchConnection.objects.filter(platform="android")
        .values_list("app", flat=True)
        .distinct()
    )
    apps = UserApp.objects.filter(id__in=apps)
    for app in apps:
        _sync_app_from_google_fit(app)


def _sync_app_from_google_fit(user_app):
    client_id = user_app.google_auth_client_id
    if not client_id:
        print("No client id found for app {}".format(user_app.name))
        return
    connections = WatchConnection.objects.filter(app=user_app, platform="android")
    for connection in connections:
        refresh_token = connection.google_fit_refresh_token
        if not refresh_token:
            print(
                "No refresh token found for app {} and user {}".format(
                    user_app.name, connection.user_uuid
                )
            )
            continue

        with GoogleFitConnection(user_app, connection) as fit_connection:
            if fit_connection._access_token is None:
                print("Access token is None")
                _mark_connection_as_logged_out(connection)
            fit_connection.get_steps_since_last_sync()


def _mark_connection_as_logged_out(connection):
    connection.google_fit_refresh_token = None
    connection.save()
