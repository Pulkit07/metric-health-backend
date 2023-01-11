import datetime
import json
import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

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

    def get_steps_since_last_sync(self):
        """
        Returns the number of steps since the last sync
        """
        # we get estimated steps and manual entry data sources and then calculate
        # the total steps as : estimated_steps - manual_entry_steps
        dataSources = self._get_specific_data_sources(
            "com.google.step_count.delta", ["estimated_steps", "user_input"]
        )
        total_steps = 0
        for name, streamId in dataSources.items():
            val = self._get_dataset_sum_for_data_source(streamId)
            total_steps += val * SOURCE_MULTIPLIER.get(name, 1)

        return (total_steps, self.start_time_in_millis, self.end_time_in_millis)

    def get_move_minutes_since_last_sync(self):
        """
        Returns the number of move minutes since the last sync
        """
        sources = self._get_specific_data_sources(
            "com.google.active_minutes",
            ["merge_active_minutes", "user_input"],
        )
        total_minutes = 0
        for name, streamId in sources.items():
            val = self._get_dataset_sum_for_data_source(streamId)
            total_minutes += val * SOURCE_MULTIPLIER.get(name, 1)

        return (total_minutes, self.start_time_in_millis, self.end_time_in_millis)

    def _get_dataset_sum_for_data_source(self, dataStreamId):
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
            total += point["value"][0]["intVal"]

        return total

    def test_sync(self):
        """
        Returns the number of steps since the last sync
        """
        # start time should be start of yesterday in Asia/Kolkata timezone in millis
        self.start_time_in_millis = int(
            datetime.datetime.now()
            .astimezone(ZoneInfo("Asia/Kolkata"))
            .replace(hour=0, minute=0, second=0, microsecond=0, day=15)
            .timestamp()
            * 1000
        )
        self.end_time_in_millis = int(
            datetime.datetime.now()
            .astimezone(ZoneInfo("Asia/Kolkata"))
            .replace(hour=0, minute=0, second=0, microsecond=0, day=16)
            .timestamp()
            * 1000
        )
        self._update_last_sync = False
        print(f"Steps since last sync are {self.get_steps_since_last_sync()}")
        print(
            f"Move minutes since last sync are {self.get_move_minutes_since_last_sync()}"
        )
