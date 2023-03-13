import hashlib
import json
import os
from watch_sdk.data_providers.fitbit import FitbitAPIClient
from watch_sdk.data_providers.google_fit import GoogleFitConnection
from .models import ConnectedPlatformMetadata, EnabledPlatform, UserApp, WatchConnection
from .constants import google_fit
import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth
import collections
import requests
import logging

logger = logging.getLogger(__name__)


def google_fit_cron():
    apps = EnabledPlatform.objects.filter(platform__name="google_fit").values_list(
        "user_app", flat=True
    )
    for app_id in apps:
        app = UserApp.objects.get(id=app_id)
        if app.webhook_url is None:
            logger.info("No webhook url specified for app %s", app)
            continue
        _sync_app_from_google_fit(app)


def _split_data_into_chunks(fitness_data):
    chunk_size = 1000
    data_chunks = []
    for data_type, data in fitness_data.items():
        for i in range(0, len(data), chunk_size):
            data_chunks.append({data_type: data[i : i + chunk_size]})
    return data_chunks


def _sync_app_from_google_fit(user_app):
    connections = WatchConnection.objects.filter(
        app=user_app,
    )
    for connection in connections:
        try:
            google_fit_connection = ConnectedPlatformMetadata.objects.get(
                connection=connection, platform__name="google_fit"
            )
        except Exception:
            continue
        if not google_fit_connection.logged_in:
            continue

        logger.debug(f"\n\nSyncing for {connection.user_uuid}")
        with GoogleFitConnection(user_app, google_fit_connection) as fit_connection:
            fitness_data = collections.defaultdict(list)
            if fit_connection._access_token is None:
                logger.debug(
                    "Unable to get access token for connection, marking it logged out"
                )
                google_fit_connection.mark_logout()
                continue
            try:
                for (
                    data_type,
                    data,
                ) in fit_connection.get_data_since_last_sync().items():
                    data_key, dclass = google_fit.RANGE_DATA_TYPES[data_type]
                    for d in data:
                        fitness_data[data_key].append(
                            dclass(
                                source="google_fit",
                                start_time=int(d[1]) / 10**6,
                                end_time=int(d[2]) / 10**6,
                                source_device=None,
                                value=d[0],
                            ).to_dict()
                        )

                if fitness_data:
                    send_data_to_webhook(
                        fitness_data,
                        user_app.webhook_url,
                        connection.user_uuid,
                        fit_connection,
                    )
            except Exception as e:
                logger.error(
                    "Unable to sync data %s, got exception %s"
                    % (connection.user_uuid, e),
                    exc_info=True,
                )
                continue


def send_data_to_webhook(fitness_data, webhook_url, user_uuid, fit_connection=None):
    chunks = _split_data_into_chunks(fitness_data)
    logger.info("got chunks %s" % len(chunks))
    cur_chunk = 0
    for chunk in chunks:
        response = requests.post(
            webhook_url,
            headers={"Content-Type": "application/json"},
            data=json.dumps({"data": chunk, "uuid": user_uuid}),
        )
        logger.info(f"response for chunk {cur_chunk}: {response}, {webhook_url}")
        cur_chunk += 1
        if response.status_code > 202 or response.status_code < 200:
            logger.error("Error in response, status code: %s" % response.status_code)
            if fit_connection:
                fit_connection._update_last_sync = False
            break


cred = credentials.Certificate(
    {
        "type": "service_account",
        "project_id": os.environ.get("FIREBASE_PROJECT_ID"),
        "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
        "private_key": os.environ.get("FIREBASE_PRIVATE_KEY"),
        "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
        "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ.get("FIREBASE_CLIENT_x509_CERT_URL"),
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


def get_hash(data):
    return hashlib.sha256(str(data).encode("utf-8")).hexdigest()
