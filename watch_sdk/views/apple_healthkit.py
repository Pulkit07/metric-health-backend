import collections
from datetime import datetime
import json
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from watch_sdk.utils import connection as connection_utils, webhook
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    DebugIosData,
    EnabledPlatform,
    IOSDataHashLog,
    Platform,
    UnprocessedData,
    UserApp,
    WatchConnection,
)

from watch_sdk.permissions import ValidKeyPermission
from watch_sdk.constants import apple_healthkit
from watch_sdk.utils.hash_utils import get_hash


logger = logging.getLogger(__name__)

SYNC_SLEEP_TYPES = set(["awake", "core", "deep", "rem"])


def _get_sleep_type(d):
    if d["value"] == 0:
        return "in_bed"
    if d["value"] == 1:
        return "asleep"
    if d["value"] == 2:
        return "awake"
    if d["value"] == 3:
        return "core"
    if d["value"] == 4:
        return "deep"
    if d["value"] == 5:
        return "rem"


def _store_unprocessed_data(connection, platform, data):
    """
    Stores the data that was not processed by the webhook due to either of following:

    * The webhook was down
    * The webhook was not set up for the app
    """
    UnprocessedData.objects.create(
        data=data,
        connection=connection,
        platform=platform,
    )


def _get_unprocessed_data(connection, platform):
    """
    Returns the unprocessed data for the given connection and platform
    """
    unprocessed_data = UnprocessedData.objects.filter(
        connection=connection, platform=platform
    )
    return [x.data for x in unprocessed_data]


@api_view(["POST"])
@permission_classes([ValidKeyPermission])
def upload_health_data_using_json_file(request):
    key = request.query_params.get("key")
    user_uuid = request.query_params.get("user_uuid")
    app = UserApp.objects.get(key=key)

    try:
        enabled_platform = EnabledPlatform.objects.get(
            user_app=app, platform__name="apple_healthkit"
        )
    except:
        logger.warn(
            f"getting apple healthkit data for app {app} which is not enabled and user {user_uuid}"
        )
        return Response(
            {"error": "Apple healthkit not enabled for this app"}, status=400
        )

    try:
        connection = WatchConnection.objects.get(app=app, user_uuid=user_uuid)
    except:
        logger.warn(
            f"getting apple healthkit data for user {user_uuid} which is not connected to app {app}"
        )
        return Response({"error": "No connection exists for this user"}, status=400)

    try:
        connected_metadata = ConnectedPlatformMetadata.objects.get(
            connection=connection, platform__name="apple_healthkit"
        )
    except:
        logger.warn(
            f"getting apple healthkit data for user {user_uuid} which is not connected to app {app}"
        )
        return Response({"error": "No connection exists for this user"}, status=400)

    logger.info(f"Health data received for {user_uuid} using a json file of app {app}")
    fitness_data = collections.defaultdict(list)
    if "data" not in request.FILES:
        logger.error(
            f"No data file found for {user_uuid} and app {app} on upload for apple healthkit"
        )
        return Response({"error": "No data file found"}, status=400)
    # read over a json file passed with the request and build fitness_data
    data = request.FILES["data"].read()
    data = json.loads(data)
    if app.id == 40:
        DebugIosData.objects.create(
            uuid=user_uuid,
            data=data,
        )
    hash = get_hash(data)
    if IOSDataHashLog.objects.filter(hash=hash, connection=connection).exists():
        logger.warn("Already processed this data")
        return Response({"success": True}, status=200)
    else:
        IOSDataHashLog.objects.create(hash=hash, connection=connection)
    total = 0
    enabled_datatypes = app.enabled_data_types.all()
    max_last_sync = 0
    for enabled in enabled_datatypes:
        data_type = apple_healthkit.DB_DATA_TYPE_KEY_MAP.get(enabled.name)
        if data_type is None:
            # skip this data type as it's not supported on apple
            continue
        key, dclass = apple_healthkit.DATATYPE_NAME_CLASS_MAP.get(
            data_type, (None, None)
        )
        if not key or not dclass:
            continue
        for d in data.get(data_type, []):
            total += 1
            start_time = d["date_from"]
            end_time = d["date_to"]
            manual_entry = (
                d.get("source_name") == "Health"
                or d.get("source_id") == "com.apple.Health"
            )
            if manual_entry and not enabled_platform.sync_manual_entries:
                continue
            if data_type == "sleep_analysis":
                value = d["date_to"] - d["date_from"]
                sleep_type = _get_sleep_type(d)
                if sleep_type not in SYNC_SLEEP_TYPES:
                    continue
                fitness_data[key].append(
                    dclass(
                        value=value,
                        start_time=start_time,
                        end_time=end_time,
                        source="apple_healthkit",
                        source_device=d.get("source_name"),
                        manual_entry=manual_entry,
                        sleep_type=sleep_type,
                    ).to_dict()
                )
            else:
                value = d["value"]
                fitness_data[key].append(
                    dclass(
                        value=value,
                        start_time=start_time,
                        end_time=end_time,
                        source="apple_healthkit",
                        source_device=d.get("source_name"),
                        manual_entry=manual_entry,
                    ).to_dict()
                )

            max_last_sync = max(max_last_sync, end_time)

    logger.info(f"Total data points received: {total}")
    unprocessed = False
    if app.webhook_url:
        if fitness_data:
            logger.info(
                f"sending {len(fitness_data)} data points to webhook from apple healthkit for {user_uuid}"
            )
            request_succeeded = webhook.send_data_to_webhook(
                fitness_data, app, connection.user_uuid, "apple_healthkit"
            )
            if not request_succeeded:
                unprocessed = True
    else:
        unprocessed = True
        logger.warn("No webhook url found, skipping and storing data locally")

    if unprocessed:
        _store_unprocessed_data(
            connection,
            Platform.objects.get(name="apple_healthkit"),
            fitness_data,
        )

    # update last sync time on server
    # TODO: we should rather update data type wise last sync
    connected_metadata.last_sync = datetime.fromtimestamp(max_last_sync / 1000)
    connected_metadata.save()
    return Response({"success": True}, status=200)
