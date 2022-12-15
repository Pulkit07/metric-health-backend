import datetime
import json
from zoneinfo import ZoneInfo
import requests

from watch_sdk.models import FitnessData


class GoogleFitConnection(object):
    """
    Encapsulates the connection to google fit for a user
    """

    def __init__(self, user_app, connection):
        self.user_app = user_app
        self.connection = connection
        self._access_token = None

    def __enter__(self):
        self._get_access_token()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._access_token = None
        if exc_type is None:
            self.connection.last_sync = datetime.datetime.now(
                tz=ZoneInfo("Asia/Kolkata")
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

    def _get_data_sources(self):
        if self._access_token is None:
            print("Access token is None")
            return
        r = requests.get(
            "https://www.googleapis.com/fitness/v1/users/me/dataSources",
            headers={"Authorization": f"Bearer {self._access_token}"},
            timeout=10,
        )
        print(r.text)

    def get_steps_since_last_sync(self):
        """
        Returns the number of steps since the last sync
        """
        if self.connection.last_sync is None:
            # set last sync time as start of today in local timezone
            last_sync_time = int(
                datetime.datetime.now()
                .astimezone(ZoneInfo("Asia/Kolkata"))
                .date()
                .timestamp()
                * 1000
            )
        else:
            last_sync_time = int(self.connection.last_sync.timestamp() * 1000)
        current_time_in_millis = int(datetime.datetime.now().timestamp() * 1000)

        response = requests.post(
            "https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate",
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                {
                    "aggregateBy": [
                        {
                            "dataTypeName": "com.google.step_count.delta",
                            "dataSourceId": "derived:com.google.step_count.delta:com.google.android.gms:estimated_steps",
                        }
                    ],
                    "bucketByTime": {"durationMillis": 86400000},
                    "startTimeMillis": last_sync_time,
                    "endTimeMillis": current_time_in_millis,
                }
            ),
            timeout=10,
        )

        if response.status_code >= 400:
            raise Exception("Error while getting steps since last sync")

        for entries in json.loads(response.text)["bucket"]:
            for entry in entries["dataset"]:
                if entry["point"]:
                    start_time = datetime.datetime.fromtimestamp(
                        int(entry["point"][0]["startTimeNanos"]) / 1000000000
                    ).astimezone(ZoneInfo("Asia/Kolkata"))
                    end_time = datetime.datetime.fromtimestamp(
                        int(entry["point"][0]["endTimeNanos"]) / 1000000000
                    ).astimezone(ZoneInfo("Asia/Kolkata"))
                    print(
                        f'today steps by {self.connection.user_uuid} from {start_time} to {end_time} are: {entry["point"][0]["value"][0]["intVal"]}'
                    )
                    FitnessData.objects.create(
                        app=self.user_app,
                        connection=self.connection,
                        start_time=start_time,
                        end_time=end_time,
                        data={"steps": entry["point"][0]["value"][0]["intVal"]},
                    )

    def get_distance_since_last_sync(self):
        pass
        # r = requests.post('https://www.googleapis.com/fitness/v1/users/me/dataset:aggregate', headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json',},
        #     data=json.dumps({
        #         'aggregateBy': [{
        #             "dataTypeName": "com.google.distance.delta",
        #             'dataSourceId': 'derived:com.google.distance.delta:com.google.android.gms:merge_distance_delta'
        #         }],
        #         'bucketByTime': {'durationMillis': 86400000},
        #         'startTimeMillis': today_start_in_millis,
        #         'endTimeMillis': current_time_in_millis
        #     }),
        # )
        # print(r.text)
