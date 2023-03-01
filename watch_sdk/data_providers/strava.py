import requests
from datetime import datetime

from watch_sdk.dataclasses import StravaCycling


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

    def get_activity_by_id(self, activity_id):
        access_token = self._get_access_token()
        response = requests.get(
            f"https://www.strava.com/api/v3/activities/{activity_id}",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if response.status_code == 200:
            return response.json()
        else:
            print("Error getting activity by id: ", response.status_code)
            return None

    def get_activities_for_first_sync(self, before):
        """
        Gets activities user did before the given timestamp
        for the first sync. For future data, we shall get it over webhook

        Gets data for 500 days before the given timestamp
        """
        access_token = self._get_access_token()
        before = datetime.now().timestamp()
        after = (
            self._last_sync.timestamp()
            if self._last_sync
            # set it to 120 days before current time
            else before - 500 * 24 * 60 * 60
        )

        activities = []
        page_number = 1
        while True:
            acts = self._get_activities_before_after(before, after, page_number, 200)
            activities.extend(acts)
            if len(acts) < 200:
                # we got less entries then page size, it means there are no more entries
                break
            page_number += 1

        return activities

    def _get_activities_before_after(self, before, after, pageNumber, pageSize):
        access_token = self._get_access_token()
        response = requests.get(
            "https://www.strava.com/api/v3/athlete/activities",
            params={
                "before": before,
                "after": after,
                "page": pageNumber,
                "per_page": pageSize,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
            },
        )

        activity_objects = []
        if response.status_code == 200:
            activities = response.json()
            for activity in activities:
                if activity["type"] != "Ride":
                    # TODO: handle other types here
                    continue
                activity_objects.append(
                    StravaCycling(
                        source="strava",
                        start_time=activity["start_date"],
                        distance=activity["distance"],
                        moving_time=activity["moving_time"],
                        total_elevation_gain=activity["total_elevation_gain"],
                        max_speed=activity["max_speed"],
                        average_speed=activity["average_speed"],
                    )
                )
            return activity_objects
        else:
            print("Error getting activities: ", response.status_code)
            return []
