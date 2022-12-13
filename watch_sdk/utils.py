import json
from watch_sdk.models import UserApp, WatchConnection
import requests


def google_fit_cron():
    apps = WatchConnection.objects.filter(platform='android').values_list('app', flat=True).distinct()
    apps = UserApp.objects.filter(id__in=apps)
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
    print('refresh token is {}'.format(connection.google_fit_refresh_token))
    print('Syncing data for app {} and user {}'.format(user_app.name, connection.user_uuid))
    print('client id is {}'.format(user_app.google_auth_client_id))
    data = requests.post('https://www.googleapis.com/oauth2/v4/token', params={
        'client_id': user_app.google_auth_client_id,
        'refresh_token': connection.google_fit_refresh_token,
        'grant_type': 'refresh_token',
    },
        headers={'Content-Type': 'application/json'}
    )
    print(data.text)
    access_token = data.json()['access_token']
    r = requests.post('https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate', headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json',},
        data=json.dumps({
            'aggregateBy': [{
                "dataTypeName": "com.google.step_count.delta",
                'dataSourceId': 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
            }],
            'bucketByTime': {'durationMillis': 86400000},
            'startTimeMillis': 1670919476000,
            'endTimeMillis': 1670919576000
        }),
    )
    print(r.text)
    pass