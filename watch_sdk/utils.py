import json
from .models import UserApp, WatchConnection
import requests
import datetime


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
    print('Syncing data for app {} and user {}'.format(user_app.name, connection.user_uuid))
    access_token = _get_access_token(user_app.google_auth_client_id, connection)
    if not access_token:
        print('Error while getting access token for app {} and user {}'.format(user_app.name, connection.user_uuid))
        return

    current_time_in_millis = int(datetime.datetime.now().timestamp() * 1000)
    one_day_ago_in_millis = current_time_in_millis - 86400000
    r = requests.post('https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate', headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json',},
        data=json.dumps({
            'aggregateBy': [{
                "dataTypeName": "com.google.step_count.delta",
                'dataSourceId': 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
            }],
            'bucketByTime': {'durationMillis': 86400000},
            'startTimeMillis': one_day_ago_in_millis,
            'endTimeMillis': current_time_in_millis
        }),
    )
    print(r.text)


def _get_access_token(google_auth_client_id, connection):
    response = requests.post('https://www.googleapis.com/oauth2/v4/token', params={
        'client_id': google_auth_client_id,
        'refresh_token': connection.google_fit_refresh_token,
        'grant_type': 'refresh_token',
    },
        headers={'Content-Type': 'application/json'}
    )
    try:
        access_token = response.json()['access_token']
    except KeyError:
        print(response.text)
        if response.status_code >= 400:
            print('Marking connection as logged out')
            _mark_connection_as_logged_out(connection)
        return

    return access_token


def _mark_connection_as_logged_out(connection):
    connection.google_fit_refresh_token = None
    connection.save()