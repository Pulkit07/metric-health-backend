import collections
from datetime import datetime
import json
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from watch_sdk.utils import connection as connection_utils, webhook
from watch_sdk.models import (
    ConnectedPlatformMetadata,
    EnabledPlatform,
    IOSDataHashLog,
    UserApp,
    WatchConnection,
)

from watch_sdk.permissions import ValidKeyPermission
from watch_sdk.constants import apple_healthkit


logger = logging.getLogger(__name__)


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
    hash = connection_utils.get_hash(data)
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
        key, dclass = apple_healthkit.DATATYPE_NAME_CLASS_MAP.get(
            data_type, (None, None)
        )
        if not key or not dclass:
            continue
        for d in data.get(data_type, []):
            total += 1
            value = d["value"]
            start_time = d["date_from"]
            end_time = d["date_to"]
            manual_entry = (
                d.get("source_name") == "Health"
                or d.get("source_id") == "com.apple.Health"
            )
            if manual_entry and not enabled_platform.sync_manual_entries:
                continue
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
    if app.webhook_url:
        if fitness_data:
            logger.info(
                f"sending {len(fitness_data)} data points to webhook from apple healthkit for {user_uuid}"
            )
            webhook.send_data_to_webhook(
                fitness_data, app, connection.user_uuid, "apple_healthkit"
            )
    else:
        logger.warn("No webhook url found, skipping")

    # update last sync time on server
    # TODO: we should rather update data type wise last sync
    connected_metadata.last_sync = datetime.fromtimestamp(max_last_sync / 1000)
    connected_metadata.save()
    return Response({"success": True}, status=200)
