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
            data = fit_connection.get_steps_since_last_sync()
            print(data)
            for entry in data:
                FitnessData.objects.create(
                    app=user_app,
                    connection=connection,
                    record_start_time=entry[0],
                    record_end_time=entry[1],
                    data={"steps": entry[2]},
                )
