import collections
from datetime import datetime
import json
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
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
from watch_sdk.utils.data_process import process_health_data
from watch_sdk.utils.hash_utils import get_hash


logger = logging.getLogger(__name__)

SYNC_SLEEP_TYPES = set(["awake", "light", "deep", "rem", "unspecified"])


def _get_sleep_type(d):
    if d["value"] == 0:
        return "in_bed"
    if d["value"] == 1:
        return "asleep"
    if d["value"] == 2:
        return "awake"
    if d["value"] == 3:
        return "light"
    if d["value"] == 4:
        return "deep"
    if d["value"] == 5:
        return "rem"

    return "unspecified"


@api_view(["POST"])
@permission_classes([ValidKeyPermission])
def upload_health_data_using_json_file(request):
    key = (
        request.query_params.get("key")
        if request.query_params.get("key")
        else request.META.get("HTTP_KEY")
    )
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

    if connected_metadata.logged_in is False:
        # we don't process data for a disconnected user
        return Response({"error": "User not connected"}, status=400)

    logger.info(f"Apple data received for {user_uuid} of {app}")
    fitness_data = collections.defaultdict(list)
    if "data" not in request.FILES:
        logger.error(
            f"No data file found for {user_uuid} and app {app} on upload for apple healthkit"
        )
        return Response({"error": "No data file found"}, status=400)
    # read over a json file passed with the request and build fitness_data
    data = request.FILES["data"].read()
    data = json.loads(data)
    if app.id == 40 or app.id == 101:
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

    if fitness_data:
        logger.info(
            f"processing {len(fitness_data)} points from apple healthkit for {user_uuid}"
        )
        process_health_data(
            fitness_data,
            connection,
            app,
            "apple_healthkit",
        )

    # update last sync time on server
    # TODO: we should rather update data type wise last sync
    connected_metadata.last_sync = datetime.fromtimestamp(max_last_sync / 1000)
    connected_metadata.save()
    return Response({"success": True}, status=200)
