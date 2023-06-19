import collections
from dataclasses import dataclass
from django.utils import timezone
import datetime
import logging
from typing import List, Optional
import requests

from watch_sdk.models import ConnectedPlatformMetadata, EnabledPlatform

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from watch_sdk.constants import google_fit

MANUALLY_ENTERED_SOURCES = set(["user_input"])

logger = logging.getLogger(__name__)
NO_OF_DAYS_OLD_DATA = 7


DATA_SOURCES_MAP = {
    "com.google.height": {
        "merge_height": "derived:com.google.height:com.google.android.gms:merge_height"
    },
    "com.google.active_minutes": {
        "merge_active_minutes": "derived:com.google.active_minutes:com.google.android.gms:merge_active_minutes",
        "user_input": "raw:com.google.active_minutes:com.google.android.apps.fitness:user_input",
    },
    "com.google.step_count.delta": {
        "estimated_steps": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
        "user_input": "raw:com.google.step_count.delta:com.google.android.apps.fitness:user_input",
    },
    "com.google.weight": {
        "merge_weight": "derived:com.google.weight:com.google.android.gms:merge_weight"
    },
    "com.google.calories.expended": {
        "merge_calories_expended": "derived:com.google.calories.expended:com.google.android.gms:merge_calories_expended",
        "user_input": "raw:com.google.calories.expended:com.google.android.apps.fitness:user_input",
    },
    "com.google.calories.bmr": {
        "merged": "derived:com.google.calories.bmr:com.google.android.gms:merged",
        "user_input": "raw:com.google.calories.bmr:com.google.android.apps.fitness:user_input",
    },
}


@dataclass
class GoogleFitPoint:
    value: float
    # in nanoseconds
    start_time: int
    # in nanoseconds
    end_time: int
    # manually entered or not
    manual_entry: bool
    # in milliseconds
    modified_time: Optional[int] = None


class GoogleFitConnection(object):
    """
    Encapsulates the connection to google fit for a user
    """

    def __init__(self, user_app, connection):
        self.user_app = user_app
        self.connection: ConnectedPlatformMetadata = connection
        self._access_token = None
        # data sources cached for the connection lifecycle
        self._cached_data_sources = None
        self._update_last_sync = True
        self._last_modified = None
        self._new_last_modified = collections.defaultdict(int)
        # find the google_fit enabled platform from app and get the client id
        self._enabled_platform = EnabledPlatform.objects.get(
            user_app=user_app, platform__name="google_fit"
        )
        self._client_id = self._enabled_platform.platform_app_id
        # whether the error was due to google server error
        # used to decide whether to mark the connection as logged out
        self._google_server_error = False

    @property
    def _data_sources(self):
        if self._cached_data_sources is None:
            self._cached_data_sources = self._get_all_data_sources()
        return self._cached_data_sources

    def __enter__(self):
        self._get_access_token()
        self._last_modified = (
            self.connection.last_modified_for_data_types
            if self.connection.last_modified_for_data_types
            else {}
        )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._access_token = None
        if exc_type is None and self._update_last_sync:
            self.connection.last_sync = datetime.datetime.now()
            if self.connection.last_modified_for_data_types is None:
                self.connection.last_modified_for_data_types = {}
            for data_type, last_modified in self._new_last_modified.items():
                self.connection.last_modified_for_data_types[data_type] = last_modified
            self.connection.save()

    def _get_access_token(self):
        """
        Get access token from google fit and update the class variable
        """
        if isinstance(self.connection.gfit_access_exp, datetime.datetime) and self.connection.gfit_access_exp > timezone.now():
            self._access_token = self.connection.gfit_access
        else:
            response = requests.post(
                "https://www.googleapis.com/oauth2/v4/token",
                params={
                    "client_id": self._client_id,
                    "refresh_token": self.connection.refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/json; charset=utf-8"},
                timeout=10,
            )
            try:
                self.connection.gfit_access = response.json()["access_token"]
                self.connection.gfit_access_exp = timezone.now() + datetime.timedelta(seconds=response.json()['expires_in'])
                self.connection.save(update_fields=['gfit_access', 'gfit_access_exp'])
                self._access_token = self.connection.gfit_access
            except KeyError:
                if response.status_code >= 400:
                    logger.warn(
                        f"GFit: error getting access token: {response.text} {response.status_code}"
                    )
                if response.status_code >= 500:
                    self._google_server_error = True

    def _perform_first_sync(self, streamName, dataStreamId, valType):
        """
        Perform first sync for the connection
        """
        logger.debug("performing first sync")
        points: List[GoogleFitPoint] = self._get_all_point_changes(
            streamName, dataStreamId, valType
        )

        if points:
            minimum_start_time = int(
                min(points, key=lambda x: int(x.start_time)).start_time
            )
        else:
            minimum_start_time = int(
                datetime.datetime.now().timestamp() * 1000 * 1000 * 1000
            )

        historical_points: List[GoogleFitPoint] = self._get_dataset_points(
            dataStreamId,
            minimum_start_time
            - NO_OF_DAYS_OLD_DATA * 24 * 60 * 60 * 1000 * 1000 * 1000,
            minimum_start_time,
            valType=valType,
        )

        points.extend(historical_points)

        return points

    def _get_specific_data_sources(self, data_type_name, data_stream_names):
        if data_type_name in DATA_SOURCES_MAP:
            return DATA_SOURCES_MAP[data_type_name]
        dataStreams = {}
        for source in self._data_sources:
            if (
                source["dataType"]["name"] == data_type_name
                and source["dataStreamName"] in data_stream_names
            ):
                dataStreams[source["dataStreamName"]] = source["dataStreamId"]

        return dataStreams

    # TODO: this can be hardcoded instead of fetched from google fit
    def _get_all_data_sources(self):
        if self._access_token is None:
            logger.debug("Access token is None")
            return
        r = requests.get(
            "https://www.googleapis.com/fitness/v1/users/me/dataSources",
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=10,
        )
        return r.json()["dataSource"]

    def _get_enabled_data_types(self):
        enabled_data_types = set()
        for source in self.user_app.enabled_data_types.all():
            # make sure data type is supported on google fit
            if source.name in google_fit.DB_DATA_TYPE_KEY_MAP:
                enabled_data_types.add(google_fit.DB_DATA_TYPE_KEY_MAP[source.name])
        return enabled_data_types

    def get_data_since_last_sync(self):
        data_points = collections.defaultdict(list)
        for data_type in self._get_enabled_data_types():
            data_streams = google_fit.RANGE_DATA_TYPES_ATTRIBUTES[data_type]
            dataSources = self._get_specific_data_sources(data_type, data_streams)
            for name, streamId in dataSources.items():
                if (
                    name in MANUALLY_ENTERED_SOURCES
                    and not self._enabled_platform.sync_manual_entries
                ):
                    continue
                if not self._last_modified or self._last_modified.get(streamId) is None:
                    vals: List[GoogleFitPoint] = self._perform_first_sync(
                        name,
                        streamId,
                        google_fit.RANGE_DATA_TYPES_UNTS[data_type],
                    )
                    data_points[data_type].extend(vals)
                else:
                    vals = self._get_all_point_changes(
                        name,
                        streamId,
                        valType=google_fit.RANGE_DATA_TYPES_UNTS[data_type],
                    )
                    data_points[data_type].extend(vals)

        return data_points

    def _get_data_point_changes(
        self,
        streamName,
        dataStreamId,
        nextPageToken,
        valType="intVal",
    ):
        response = requests.get(
            f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{dataStreamId}/dataPointChanges/",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            params={"limit": 1000, "pageToken": nextPageToken},
            timeout=10,
        )

        if response.status_code != 200:
            # We occasionally gets 503 Service Unavailable from google fit
            logger.debug(response.text)
            logger.debug(
                "Error while fetching data point changes, got status code %s"
                % response.status_code
            )
            raise Exception("Error while fetching data point changes")

        points: List[GoogleFitPoint] = []
        for point in response.json()["insertedDataPoint"]:
            points.append(
                GoogleFitPoint(
                    point["value"][0][valType],
                    point["startTimeNanos"],
                    point["endTimeNanos"],
                    streamName in MANUALLY_ENTERED_SOURCES,
                    point["modifiedTimeMillis"],
                )
            )

        return (points, response.json()["nextPageToken"])

    def _get_all_point_changes(self, streamName, dataStreamId, valType="intVal"):
        res: List[GoogleFitPoint] = []
        nextPageToken = None
        try:
            while True:
                points, nextPageToken = self._get_data_point_changes(
                    streamName, dataStreamId, nextPageToken, valType=valType
                )
                if not points:
                    break
                res.extend(points)
        except Exception as e:
            logger.debug(e)
            logger.debug("Error while fetching data point changes")
            # reset whatever data points we have received
            res = []

        points: List[GoogleFitPoint] = []
        for point in res:
            if self._last_modified and int(
                point.modified_time
            ) <= self._last_modified.get(dataStreamId, 0):
                continue
            points.append(
                GoogleFitPoint(
                    point.value,
                    point.start_time,
                    point.end_time,
                    point.manual_entry,
                )
            )
            self._new_last_modified[dataStreamId] = max(
                self._new_last_modified[dataStreamId], int(point.modified_time)
            )

        return points

    def _get_dataset_points(
        self,
        dataStreamId,
        start_time_in_nanos,
        end_time_in_nanos,
        valType="intVal",
    ):
        logger.debug("getting dataset points")
        response = requests.get(
            f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{dataStreamId}/datasets/"
            f"{start_time_in_nanos}-{end_time_in_nanos}",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        vals: List[GoogleFitPoint] = []
        for point in response.json()["point"]:
            vals.append(
                GoogleFitPoint(
                    point["value"][0][valType],
                    int(point["startTimeNanos"]),
                    int(point["endTimeNanos"]),
                    None,
                )
            )
            if valType == "unknown":
                logger.debug(point)
                continue

        return vals

    def test_sync(self):
        """
        Returns the number of steps since the last sync
        """
        # start time should be start of yesterday in Asia/Kolkata timezone in millis
        self._update_last_sync = False
        self._last_modified = {}
        data = self.get_data_since_last_sync()
        date_wise_map = collections.defaultdict(int)
        for key, values in data.items():
            for value in values:
                start_date = datetime.datetime.fromtimestamp(
                    int(value.start_time) / 10**9, tz=ZoneInfo("Asia/Kolkata")
                ).date()
                date_wise_map[start_date] += value.value
                if value.manual_entry:
                    print(f"manually entered {value}")

        import pdb

        pdb.set_trace()
