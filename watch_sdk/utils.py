import datetime
from watch_sdk.google_fit import GoogleFitConnection
from .models import FitnessData, UserApp, WatchConnection
import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth
import os


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
                (
                    total_steps,
                    start_time,
                    end_time,
                ) = fit_connection.get_steps_since_last_sync()
                FitnessData.objects.create(
                    app=user_app,
                    connection=connection,
                    record_start_time=datetime.datetime.fromtimestamp(
                        start_time / 1000
                    ),
                    record_end_time=datetime.datetime.fromtimestamp(end_time / 1000),
                    data={"steps": total_steps},
                    data_source="google_fit",
                )
            except Exception as e:
                print(
                    "Unable to get steps since last sync for user %s"
                    % connection.user_uuid
                )
                continue

            try:
                (
                    total_move_minutes,
                    start_time,
                    end_time,
                ) = fit_connection.get_move_minutes_since_last_sync()
                FitnessData.objects.create(
                    app=user_app,
                    connection=connection,
                    record_start_time=datetime.datetime.fromtimestamp(
                        start_time / 1000
                    ),
                    record_end_time=datetime.datetime.fromtimestamp(end_time / 1000),
                    data={"move_minutes": total_move_minutes},
                    data_source="google_fit",
                )
            except Exception as e:
                print(
                    "Unable to get move minutes since last sync for user %s"
                    % connection.user_uuid
                )
                continue


cred = credentials.Certificate(
    {
        "type": "service_account",
        "project_id": "taphealth",
        "private_key_id": "f5b7251010e0befa498c934bc02359f463188fb3",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCzs1lWD16hTPP4\nITBhTH0guj0NEZF1p+9PwVrEteFAsZw9Bud/+4VdDlwifMJMph5+CtzjskPiFirh\nzLENtkQjIrpG1CmaybrMq4mxD/xWTGd8ZSsLsp6Pma/SCX1erqHXHr/lRNI+ahuY\nNV90SfuTqtQNtY5RlTeqd+64/od/zHbcW5uD2JtizydIEb/12mIQthMShlk2tZDY\nx+YaEj/XQY+UW3niuBfA3/EteGjjOxImYu5gsb39UQ690rqpL36EmHZA77cp/cI3\nEitWKXnkObG5jCcYQGw705uFrfrEl3a/guAo/Wdw/6rW8+FaEbA6Kc4iLajvBQ8I\nEC1EGcShAgMBAAECggEAALn8HViyCgcqZmH54WamBlXZBxQQPCMwitenzHZnFcY4\nT5JUW1tSGC/elp5/M0vISYQT/OMnLg/F7Mh4X9JAj5LCt5kyxP4K7PHGVYRQgaIz\n4Odj+kqmqfqn9EWxM6ENzvhnM/IAEP2TQ64usLLMOHNPDNwCF4z0MRgnYcpYbTLh\nSdWsqYhbxqyn7Q5N7csu1VfJeg+RqLAohc14iPP5Q88FqpEdntMlmnzagpSJ2FuH\nJMaP2iOIdA9iF1OEJkdxRMgwSiUQpNyPLXov8NMfnIaBkeO3RRxFUbnijNShRlB2\nNQJg642pyT/25hamQhEoVB7iCu5EWk+qAA53rCoQCQKBgQDnb8lYG4EWTFoSzRAl\nKbCoTaslOZ9+zPCLtz9nEf9P/stj2+p6SxCEzlwhh6ddf2pYU0ONIxn56DW0Brsz\nT6CRxTbwjXzk7OIFtZpeRzfH/bObi0A8zc9ad/a7+R+e9FMb5c9ZjJyxnN8UXbq6\nZ3MaANpzlHjjMyUKNZu44o8+3wKBgQDGxeAWTOPofXcFNzvinxBVsY5LweD9nrV7\nt4KKd+nPX4kpbdW40tFAtitNINALnc4D4vNAoxdnYnn6wSIeBa7zwZXr9rKVkLgN\n4gdxwyQFFJ6cj9u5b0PKBHwSG6xVxrESxU6whF+VhiX9QmBjrAWLqbr9Y/yLCRIL\nTzA+FWzsfwKBgQCOR5j+g5oufS361PqR/jlOnsESl4RITfGr0zI1SUkugrPDZlWW\nbUNwgfT94AmyXzyfpECpKeU0T9+EF4dKmi9armWCKVmY21Bwth56y0mtt3iNrWQG\nfXh2Y73Z/ePEsuvNANEiemFyh8BVIvJC2opWeCPUXnibJLwmtKJRXWc2/QKBgBlS\nigqtPveWTDxY3gMv2mfgV81k5KHKvzoEldfIEPw/In0ppemGyeuhiYCo5ngkYWNz\nXSPl4wxjqkB8rDkA5lndVpkZ84RETH5QRjyC7KrNBqvRU9+awhsRWTEBX4IJ7vMC\nOdUY+AhXb62E8DyiZI53UAAJ5dlcjXTtYKr4FclHAoGAHPMWQPEiq0bdqXnULeso\n20saVvkmDnfkE3KQHBJ0o3dh927fTBdox+cZ2M20UGMgrp4ujmqMhdu9UJkY58Yn\nNihO45LISm9sM3sdoXYfy4Mz0gdf1ZxTsqy1PkIpAzsWs0DRHg0YUVpRDKYlO/SZ\nKn9JAe8c3QQpZKFrAe7InM4=\n-----END PRIVATE KEY-----\n",
        "client_email": "firebase-adminsdk-1uv07@taphealth.iam.gserviceaccount.com",
        "client_id": "106694276624459499381",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-1uv07%40taphealth.iam.gserviceaccount.com",
    },
)

default_app = firebase_admin.initialize_app(cred)


def verify_firebase_token(auth_token):
    if not auth_token:
        return False
    try:
        decoded_token = auth.verify_id_token(auth_token)
    except Exception:
        return False

    try:
        decoded_token["uid"]
        return True
    except Exception:
        return False
