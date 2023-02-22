import base64
import requests
from watch_sdk.models import ConnectedPlatformMetadata


class FitbitAPIClient(object):
    def __init__(self, user_app, connection):
        self.user_app = user_app
        self.connection: ConnectedPlatformMetadata = connection
        self._access_token = None
        self._refresh_token = connection.refresh_token
        enabled_platform = user_app.enabled_platforms.get(platform__name="fitbit")
        self._client_id = enabled_platform.platform_app_id
        self._client_secret = enabled_platform.platform_app_secret

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
        import pdb

        pdb.set_trace()
        if response.status_code == 200:
            response_data = response.json()
            self._access_token = response_data["access_token"]
            self._refresh_token = response_data["refresh_token"]
        elif response.status_code == 401:
            self._refresh_token = None
            # mark the connection as logged out as Fitbit requires user to re-authenticate
            self.connection.logged_in = False
