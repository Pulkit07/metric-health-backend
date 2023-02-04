import collections
import datetime
import requests

from watch_sdk.models import ConnectedPlatformMetadata

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from .constants import google_fit

SOURCE_MULTIPLIER = {
    "user_input": -1,
}


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
        self._client_id = user_app.enabled_platforms.get(
            platform__name="google_fit"
        ).platform_app_id

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
        response = requests.post(
            "https://www.googleapis.com/oauth2/v4/token",
            params={
                "client_id": self._client_id,
                "refresh_token": self.connection.refresh_token,
                "grant_type": "refresh_token",
            },
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        try:
            self._access_token = response.json()["access_token"]
        except KeyError:
            print(response.text)
            if response.status_code >= 400:
                print("Status code is more than 400")

    def _perform_first_sync(self, dataStreamId, valType):
        """
        Perform first sync for the connection
        """
        print("performing first sync")
        points = self._get_all_point_changes(dataStreamId, valType)

        minimum_start_time = int(min(points, key=lambda x: int(x[1]))[1])

        historical_points = self._get_dataset_points(
            dataStreamId,
            minimum_start_time - 120 * 24 * 60 * 60 * 1000 * 1000 * 1000,
            minimum_start_time,
            valType=valType,
        )

        points.extend(historical_points)

        return points

    def _get_specific_data_sources(self, data_type_name, data_stream_names):
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
            print("Access token is None")
            return
        r = requests.get(
            "https://www.googleapis.com/fitness/v1/users/me/dataSources",
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=10,
        )
        return r.json()["dataSource"]

    def get_data_since_last_sync(self):
        data_points = collections.defaultdict(list)
        for data_type, data_streams in google_fit.RANGE_DATA_TYPES_ATTRIBUTES.items():
            dataSources = self._get_specific_data_sources(data_type, data_streams)
            for name, streamId in dataSources.items():
                if not self._last_modified or self._last_modified.get(streamId) is None:
                    data_points[data_type].extend(
                        self._perform_first_sync(
                            streamId,
                            google_fit.RANGE_DATA_TYPES_UNTS[data_type],
                        )
                    )
                else:
                    vals = self._get_all_point_changes(
                        streamId,
                        valType=google_fit.RANGE_DATA_TYPES_UNTS[data_type],
                    )
                    data_points[data_type].extend(vals)

        return data_points

    def _get_data_point_changes(
        self,
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
        )

        points = []
        for point in response.json()["insertedDataPoint"]:
            points.append(
                (
                    point["value"][0][valType],
                    point["startTimeNanos"],
                    point["endTimeNanos"],
                    point["modifiedTimeMillis"],
                )
            )

        return (points, response.json()["nextPageToken"])

    def _get_all_point_changes(self, dataStreamId, valType="intVal"):
        res = []
        nextPageToken = None
        while True:
            points, nextPageToken = self._get_data_point_changes(
                dataStreamId, nextPageToken, valType=valType
            )
            if not points:
                break
            res.extend(points)

        points = []
        for point in res:
            if self._last_modified and int(point[3]) <= self._last_modified.get(
                dataStreamId, 0
            ):
                continue
            points.append(
                (
                    point[0],
                    point[1],
                    point[2],
                )
            )
            self._new_last_modified[dataStreamId] = max(
                self._new_last_modified[dataStreamId], int(point[3])
            )

        return points

    def _get_dataset_points(
        self,
        dataStreamId,
        start_time_in_nanos,
        end_time_in_nanos,
        valType="intVal",
    ):
        print("getting dataset points")
        response = requests.get(
            f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{dataStreamId}/datasets/"
            f"{start_time_in_nanos}-{end_time_in_nanos}",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        vals = []
        for point in response.json()["point"]:
            vals.append(
                (
                    point["value"][0][valType],
                    int(point["startTimeNanos"]),
                    int(point["endTimeNanos"]),
                )
            )
            if valType == "unknown":
                print(point)
                continue

        return vals

    def test_sync(self):
        """
        Returns the number of steps since the last sync
        """
        # start time should be start of yesterday in Asia/Kolkata timezone in millis
        self._update_last_sync = False
        data = self.get_data_since_last_sync()
        date_wise_map = collections.defaultdict(int)
        for key, values in data.items():
            for value in values:
                start_date = datetime.datetime.fromtimestamp(
                    int(value[1]) / 10**9, tz=ZoneInfo("Asia/Kolkata")
                ).date()
                date_wise_map[start_date] += value[0]
        import pdb

        pdb.set_trace()
