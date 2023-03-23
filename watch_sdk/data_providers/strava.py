import collections
import logging
import uuid
import requests
from datetime import datetime

from watch_sdk.dataclasses import StravaCycling
from watch_sdk.models import EnabledPlatform

logger = logging.getLogger(__name__)

SUPPORTED_TYPES = {
    "Ride": StravaCycling,
    # "Run": StravaRun,
    # "Walk": StravaWalk,
}


class StravaAPIClient(object):
    def __init__(self, user_app, platform_connection, user_uuid):
        self._user_app = user_app
        self._platform_connection = platform_connection
        self._user_uuid = user_uuid
        self._access_token = None
        self.refresh_token = platform_connection.refresh_token
        self._last_sync = platform_connection.last_sync
        self.enabled_platform = user_app.enabled_platforms.get(platform__name="strava")
        self._client_id = self.enabled_platform.platform_app_id
        self._client_secret = self.enabled_platform.platform_app_secret

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
            logger.error("Error refreshing access token: ", response.status_code)
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
            # TODO: convert to our dataclass and then return
            return response.json()
        else:
            logger.error("Error getting activity by id: ", response.status_code)
            return None

    def get_activities_since_last_sync(self, before):
        """
        Gets activities user did before the given timestamp
        for the first sync. For future data, we shall get it over webhook

        Gets data for 500 days before the given timestamp
        """
        before = datetime.now().timestamp()
        after = (
            self._last_sync.timestamp()
            if self._last_sync
            # set it to 120 days before current time
            else before - 500 * 24 * 60 * 60
        )

        activities = collections.defaultdict(list)
        page_number = 1
        while True:
            acts = self._get_activities_before_after(before, after, page_number, 200)
            for act_type, act in acts.items():
                activities[act_type].extend(act)
                for a in act:
                    self._last_sync = max(a.end_time, self._last_sync)
            if sum([len(act) for act in acts.values()]) < 200:
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

        activity_objects = collections.defaultdict(list)
        if response.status_code == 200:
            activities = response.json()
            for activity in activities:
                if activity["type"] not in SUPPORTED_TYPES:
                    continue

                if activity["manual"] and not self.enabled_platform.sync_manual_entries:
                    continue

                # TODO: make it generic
                if activity["type"] == "Ride":
                    activity_objects["strava_cycling"].append(
                        SUPPORTED_TYPES[activity["type"]](
                            source="strava",
                            start_time=activity["start_date"],
                            distance=activity["distance"],
                            moving_time=activity["moving_time"],
                            total_elevation_gain=activity["total_elevation_gain"],
                            max_speed=activity["max_speed"],
                            average_speed=activity["average_speed"],
                            source_device=None,
                            manual_entry=activity["manual"],
                        )
                    )

            return activity_objects
        else:
            logger.error("Error getting activities: ", response.status_code)
            return []


def _get_callback_url(app):
    # TODO: fix this and get the host from env
    return f"https://apidev.hekahealth.co/watch_sdk/strava/{app.id}/webhook"


def create_strava_subscription(app):
    enabled_platform = EnabledPlatform.objects.get(
        user_app=app, platform__name="strava"
    )
    if enabled_platform.webhook_verify_token is None:
        enabled_platform.webhook_verify_token = uuid.uuid4()
        enabled_platform.save()

    callback_url = _get_callback_url(app)

    response = requests.post(
        "https://www.strava.com/api/v3/push_subscriptions",
        params={
            "client_id": enabled_platform.platform_app_id,
            "client_secret": enabled_platform.platform_app_secret,
            "callback_url": callback_url,
            "verify_token": enabled_platform.webhook_verify_token,
        },
    )

    if response.status_code == 201:
        response_data = response.json()
        enabled_platform.webhook_id = response_data["id"]
        enabled_platform.save()
        logger.info("Created subscription")
    else:
        logger.error(
            "Error creating subscription: ", response.status_code, response.json()
        )


def get_strava_subscriptions(app):
    enabled_platform = EnabledPlatform.objects.get(
        user_app=app, platform__name="strava"
    )
    response = requests.get(
        "https://www.strava.com/api/v3/push_subscriptions",
        params={
            "client_id": enabled_platform.platform_app_id,
            "client_secret": enabled_platform.platform_app_secret,
        },
    )

    if response.status_code == 200:
        response_data = response.json()
        logger.debug("Got subscriptions", response_data)
    else:
        logger.error(
            "Error getting subscriptions: ", response.status_code, response.json()
        )


def delete_strava_subscription(app):
    enabled_platform = EnabledPlatform.objects.get(
        user_app=app, platform__name="strava"
    )
    response = requests.delete(
        "https://www.strava.com/api/v3/push_subscriptions/{}".format(
            enabled_platform.webhook_id
        ),
        params={
            "client_id": enabled_platform.platform_app_id,
            "client_secret": enabled_platform.platform_app_secret,
        },
    )

    if response.status_code == 204:
        enabled_platform.webhook_id = None
        enabled_platform.webhook_verify_token = None
        enabled_platform.save()
        logger.info("Deleted subscription")
    else:
        logger.error(
            "Error deleting subscription: ", response.status_code, response.json()
        )
