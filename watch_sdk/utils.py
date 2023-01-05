import datetime
from watch_sdk.google_fit import GoogleFitConnection
from .models import FitnessData, UserApp, WatchConnection


def google_fit_cron():
    apps = UserApp.objects.filter(google_auth_client_id__isnull=False)
    for app in apps:
        _sync_app_from_google_fit(app)


def _sync_app_from_google_fit(user_app):
    connections = WatchConnection.objects.filter(
        app=user_app,
        platform="android",
        google_fit_refresh_token__isnull=False,
        logged_in=True,
    )
    for connection in connections:
        with GoogleFitConnection(user_app, connection) as fit_connection:
            if fit_connection._access_token is None:
                print("Unable to get access token")
                connection.mark_logout()
                continue
            try:
                total_steps = fit_connection.get_steps_since_last_sync()
            except Exception as e:
                print(
                    "Unable to get steps since last sync for user %s"
                    % connection.user_uuid
                )
                continue

            try:
                total_move_minutes = fit_connection.get_move_minutes_since_last_sync()
            except Exception as e:
                print(
                    "Unable to get move minutes since last sync for user %s"
                    % connection.user_uuid
                )
                continue
            FitnessData.objects.create(
                app=user_app,
                connection=connection,
                record_start_time=datetime.datetime.fromtimestamp(
                    fit_connection.start_time_in_millis / 1000
                ),
                record_end_time=datetime.datetime.fromtimestamp(
                    fit_connection.end_time_in_millis / 1000
                ),
                data={
                    "steps": total_steps,
                    "move_minutes": total_move_minutes,
                },
                data_source="google_fit",
            )
