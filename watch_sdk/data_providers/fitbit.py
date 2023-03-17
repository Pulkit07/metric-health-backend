import base64
import logging
import requests
import uuid
from watch_sdk.models import ConnectedPlatformMetadata, EnabledPlatform


logger = logging.getLogger(__name__)


class FitbitAPIClient(object):
    def __init__(self, user_app, connection, user_uuid, refresh_token=None):
        self.user_app = user_app
        self.connection: ConnectedPlatformMetadata = connection
        self.user_uuid = user_uuid
        self._access_token = None
        self._refresh_token = (
            refresh_token if refresh_token else connection.refresh_token
        )
        enabled_platform = EnabledPlatform.objects.get(
            user_app=user_app, platform__name="fitbit"
        )
        self._client_id = enabled_platform.platform_app_id
        self._client_secret = enabled_platform.platform_app_secret
        if self.connection.platform_connection_uuid is None:
            self.connection.platform_connection_uuid = str(uuid.uuid4())

    def __enter__(self):
        self._get_access_token()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._access_token = None
        if self._refresh_token != self.connection.refresh_token:
            self.connection.refresh_token = self._refresh_token
            self.connection.save()

    def _get_access_token(self):
        if self._access_token is None:
            self._refresh_access_token()
        return self._access_token

    def _refresh_access_token(self):
        if self._refresh_token is None:
            raise Exception("No refresh token found")
        response = requests.post(
            "https://api.fitbit.com/oauth2/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": "Basic "
                + base64.b64encode(
                    (self._client_id + ":" + self._client_secret).encode("ascii")
                ).decode("ascii"),
            },
            data={
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
            },
        )

        if response.status_code == 200:
            response_data = response.json()
            self._access_token = response_data["access_token"]
            self._refresh_token = response_data["refresh_token"]
        elif response.status_code == 401:
            self._refresh_token = None
            # mark the connection as logged out as Fitbit requires user to re-authenticate
            self.connection.logged_in = False

    def create_subscription(self):
        response = requests.post(
            f"https://api.fitbit.com/1/user/-/apiSubscriptions/{self.connection.platform_connection_uuid}.json",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self._get_access_token(),
            },
        )

        if response.status_code == 200:
            logger.warn(
                "Fitbit subscription already exist with same user/subscription id"
            )
        elif response.status_code == 201:
            logger.info("Fitbit subscription created successfully")
        elif response.status_code == 409:
            logger.warn(
                "Fitbit subscription already exist with different user/subscription id"
            )
        else:
            logger.error(
                "Error creating Fitbit subscription, status code: ",
                response.status_code,
            )

    def delete_subscription(self):
        response = requests.delete(
            f"https://api.fitbit.com/1/user/-/apiSubscriptions/{self.connection.platform_connection_uuid}.json",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self._get_access_token(),
            },
        )
        logger.info(
            "Fitbit subscription deleted successfully, response: ", str(response)
        )
