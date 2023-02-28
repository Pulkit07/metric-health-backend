import requests
from datetime import datetime


class StravaAPIClient(object):
    def __init__(self, user_app, platform_connection, user_uuid):
        self._user_app = user_app
        self._platform_connection = platform_connection
        self._user_uuid = user_uuid
        self._access_token = None
        self.refresh_token = platform_connection.refresh_token
        self._last_sync = platform_connection.last_sync
        enabled_platform = user_app.enabled_platforms.get(platform__name="strava")
        self._client_id = enabled_platform.platform_app_id
        self._client_secret = enabled_platform.platform_app_secret

    def __enter__(self):
        self._get_access_token()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._access_token = None
        if self.refresh_token != self._platform_connection.refresh_token:
            self._platform_connection.refresh_token = self.refresh_token
            self._platform_connection.save()

        if self._last_sync != self._platform_connection.last_sync:
            self._platform_connection.last_sync = self._last_sync
            self._platform_connection.save()

    def _get_access_token(self):
        if self._access_token is None:
            self._refresh_access_token()
        return self._access_token

    def _refresh_access_token(self):
        if self.refresh_token is None:
            raise Exception("No refresh token available")

        response = requests.post(
            "https://www.strava.com/oauth/token",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
            },
        )

        if response.status_code == 200:
            response_data = response.json()
            self._access_token = response_data["access_token"]
            self.refresh_token = response_data["refresh_token"]
        else:
            print("Error refreshing access token: ", response.status_code)
            self.refresh_token = None
            # mark the connection as logged out as Strava requires user to re-authenticate
            self._platform_connection.logged_in = False

    def get_activities_since_last_sync(self):
        access_token = self._get_access_token()
        import pdb

        pdb.set_trace()
        before = datetime.now().timestamp()
        after = (
            self._last_sync.timestamp()
            if self._last_sync
            # set it to 120 days before current time
            else before - 500 * 24 * 60 * 60
        )

        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            params={
                "before": before,
                "after": after,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        if response.status_code == 200:
            activities = response.json()
            self._last_sync = datetime.fromtimestamp(before)
            return activities
        else:
            print("Error getting activities: ", response.status_code)
            return []
