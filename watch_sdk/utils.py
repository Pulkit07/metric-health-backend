from watch_sdk.models import WatchConnection

def google_fit_cron():
    apps = WatchConnection.objects.filter(platform='android').values_list('app', flat=True).distinct()
    for app in apps:
        _sync_app_from_google_fit(app)

def _sync_app_from_google_fit(user_app):
    client_id = user_app.google_auth_client_id
    if not client_id:
        print('No client id found for app {}'.format(user_app.name))
        return
    connections = WatchConnection.objects.filter(app=user_app, platform='android')
    for connection in connections:
        refresh_token = connection.google_fit_refresh_token
        if not refresh_token:
            print('No refresh token found for app {} and user {}'.format(user_app.name, connection.user_uuid))
            continue
        _sync_google_fit_for_connection(user_app, connection)


def _sync_google_fit_for_connection(user_app, connection):
    print('Syncing data for app {} and user {}'.format(user_app.name, connection.user_uuid))
    pass