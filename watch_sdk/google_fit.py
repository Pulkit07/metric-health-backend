import datetime
import json
import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from . import constants

SOURCE_MULTIPLIER = {
    "user_input": -1,
}


class GoogleFitConnection(object):
    """
    Encapsulates the connection to google fit for a user
    """

    def __init__(self, user_app, connection):
        self.user_app = user_app
        self.connection = connection
        self._access_token = None
        self.start_time_in_millis = None
        self.end_time_in_millis = None
        # data sources cached for the connection lifecycle
        self._cached_data_sources = None
        self._update_last_sync = True

    @property
    def _data_sources(self):
        if self._cached_data_sources is None:
            self._cached_data_sources = self._get_all_data_sources()
        return self._cached_data_sources

    def __enter__(self):
        self._get_access_token()
        self.end_time_in_millis = int(datetime.datetime.now().timestamp() * 1000)
        if self.connection.last_sync is None:
            # set start time as 120 days before todays date
            self.start_time_in_millis = int(
                (
                    datetime.datetime.now().replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                    - datetime.timedelta(days=120)
                ).timestamp()
                * 1000
            )
        else:
            self.start_time_in_millis = int(
                self.connection.last_sync.timestamp() * 1000
            )
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._access_token = None
        if exc_type is None and self._update_last_sync:
            self.connection.last_sync = datetime.datetime.fromtimestamp(
                self.end_time_in_millis / 1000.0
            )
            self.connection.save()

    def _get_access_token(self):
        """
        Get access token from google fit and update the class variable
        """
        response = requests.post(
            "https://www.googleapis.com/oauth2/v4/token",
            params={
                "client_id": self.user_app.google_auth_client_id,
                "refresh_token": self.connection.google_fit_refresh_token,
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

    def _get_specific_data_sources(self, data_type_name, data_stream_names):
        dataStreams = {}
        for source in self._data_sources:
            if (
                source["dataType"]["name"] == data_type_name
                and source["dataStreamName"] in data_stream_names
            ):
                dataStreams[source["dataStreamName"]] = source["dataStreamId"]

        return dataStreams

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

    def get_data_for_point_types(self):
        data_points = {}
        for data_type, data_streams in constants.POINT_DATA_TYPES_ATTRIBUTES.items():
            dataSources = self._get_specific_data_sources(data_type, data_streams)
            data_points[data_type] = []
            for _, streamId in dataSources.items():
                data_points[data_type].extend(
                    self._get_data_points_for_data_source(
                        streamId,
                        valType=constants.POINT_DATA_TYPES_UNITS[data_type],
                    )
                )

        return data_points

    def get_data_for_range_types(self):
        data_points = {}
        for data_type, data_streams in constants.RANGE_DATA_TYPES_ATTRIBUTES.items():
            dataSources = self._get_specific_data_sources(data_type, data_streams)
            total = 0
            for name, streamId in dataSources.items():
                val = self._get_dataset_sum_for_data_source(
                    streamId,
                    valType=constants.RANGE_DATA_TYPES_UNTS[data_type],
                )
                total += val * SOURCE_MULTIPLIER.get(name, 1)
            data_points[data_type] = (
                (total, self.start_time_in_millis, self.end_time_in_millis),
            )

        return data_points

    def _get_data_points_for_data_source(self, dataSreamId, valType="intVal"):
        response = requests.get(
            f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{dataSreamId}/datasets/"
            f"{self.start_time_in_millis * 1000000}-{self.end_time_in_millis * 1000000}",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )

        points = []
        for point in response.json()["point"]:
            if valType == "unknown":
                print(point)
                continue
            points.append(
                (
                    point["value"][0][valType],
                    point["startTimeNanos"],
                    point["endTimeNanos"],
                )
            )

        return points

    def _get_dataset_sum_for_data_source(self, dataStreamId, valType="intVal"):
        response = requests.get(
            f"https://www.googleapis.com/fitness/v1/users/me/dataSources/{dataStreamId}/datasets/"
            f"{self.start_time_in_millis * 1000000}-{self.end_time_in_millis * 1000000}",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        total = 0
        for point in response.json()["point"]:
            if valType == "unknown":
                print(point)
                continue
            total += point["value"][0][valType]

        return total

    def test_sync(self):
        """
        Returns the number of steps since the last sync
        """
        # start time should be start of yesterday in Asia/Kolkata timezone in millis
        self.start_time_in_millis = int(
            (
                datetime.datetime.now().replace(
                    hour=0, minute=0, second=0, microsecond=0
                )
                - datetime.timedelta(days=365)
            ).timestamp()
            * 1000
        )
        self.end_time_in_millis = int(
            datetime.datetime.now()
            .astimezone(ZoneInfo("Asia/Kolkata"))
            .replace(hour=0, minute=0, second=0, microsecond=0, day=11)
            .timestamp()
            * 1000
        )
        self._update_last_sync = False
        print(f"Data sum for various points is {self.get_data_for_range_types()}")
        print(f"Data points for various values are {self.get_data_for_point_types()}")
