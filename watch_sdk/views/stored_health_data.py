# APIs to return health data stored on our servers

import datetime
from zoneinfo import ZoneInfo
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum
from watch_sdk.data_providers.google_fit import GoogleFitConnection

from watch_sdk.models import (
    ConnectedPlatformMetadata,
    HealthDataEntry,
    UserApp,
    WatchConnection,
)
from watch_sdk.permissions import ValidKeyPermission


@api_view(["GET"])
@permission_classes([ValidKeyPermission])
def aggregated_data_for_timerange(request):
    """
    Returns the aggregated data for a given time range

    Request params:
      - user_uuid: the uuid of the user for whom the data is to be fetched

    Request body:
      - platform: the name of the platform (eg. google_fit, apple_healthkit, etc.)
      - data_type: the name of data type (eg. steps, calories, etc.)
      - start_time: the start time of the range (in milliseconds since epoch)
      - end_time: the end time of the range (in milliseconds since epoch)
    """
    key = request.META.get("HTTP_KEY")
    uuid = request.query_params.get("user_uuid")

    try:
        connection = WatchConnection.objects.get(app__key=key, user_uuid=uuid)
    except WatchConnection.DoesNotExist:
        return Response({"error": "Access denied"}, status=401)

    platform = request.data.get("platform")
    data_type = request.data.get("data_type")
    start_time = request.data.get("start_time")
    end_time = request.data.get("end_time")

    # check if any of the above is None and if yes, return error response
    if not all([platform, data_type, start_time, end_time]):
        return Response({"error": "Missing parameters"}, status=400)

    if platform == "google_fit":
        # hit GFit APIs for now
        cpm = ConnectedPlatformMetadata.objects.get(
            connection=connection, platform__name="google_fit"
        )
        total = 0
        with GoogleFitConnection(connection.app, cpm) as gfc:
            total_vals = gfc.get_aggregated_data_for_timerange(
                data_type,
                start_time,
                end_time,
                bucket_size=None,
            )

            if total_vals:
                total = total_vals[0].value

        return Response({"total": total})

    try:
        start_time = datetime.datetime.fromtimestamp(start_time / 10**3)
    except Exception:
        return Response({"error": "Invalid start time"}, status=400)

    try:
        end_time = datetime.datetime.fromtimestamp(end_time / 10**3)
    except Exception:
        return Response({"error": "Invalid end time"}, status=400)

    total = HealthDataEntry.objects.filter(
        user_connection=connection,
        source_platform__name=platform,
        data_type__name=data_type,
        start_time__gte=start_time,
        end_time__lte=end_time,
    ).aggregate(Sum("value"))

    print_synced_uuids()
    _show_date_wise_data(connection, platform, data_type)

    return Response({"total": total["value__sum"]})


@api_view(["GET"])
@permission_classes([ValidKeyPermission])
def get_date_wise_data(request):
    """
    Returns a list of date wise data for a given time range

    Response:

    {
        "data": [
            {
                # date in milliseconds since epoch
                "start_time": 182347102000,
                "end_time": 182347102000,
                "value": 1000
            },
            ...
        ],
    }
    """
    key = request.META.get("HTTP_KEY")
    uuid = request.query_params.get("user_uuid")

    try:
        connection = WatchConnection.objects.get(app__key=key, user_uuid=uuid)
    except WatchConnection.DoesNotExist:
        return Response({"error": "Access denied"}, status=401)

    platform = request.data.get("platform")
    data_type = request.data.get("data_type")
    start_time = request.data.get("start_time")
    end_time = request.data.get("end_time")

    if not all([platform, data_type, start_time, end_time]):
        return Response({"error": "Missing parameters"}, status=400)

    if platform == "google_fit":
        # hit GFit APIs for now
        cpm = ConnectedPlatformMetadata.objects.get(
            connection=connection, platform__name="google_fit"
        )
        entries = []
        with GoogleFitConnection(connection.app, cpm) as gfc:
            vals = gfc.get_aggregated_data_for_timerange(
                data_type,
                start_time,
                end_time,
            )

            for v in vals:
                entries.append(
                    {
                        "start_time": v.start_time / 10**3,
                        "end_time": v.end_time / 10**3,
                        "value": v.value,
                    }
                )

        return Response({"data": entries})

    else:
        return Response({"error": "Platform not supported"}, status=400)


@api_view(["GET"])
@permission_classes([ValidKeyPermission])
def get_menstruation_data(request):
    """
    Returns the menstrual data for a given time range

    Request params:
      - user_uuid: the uuid of the user for whom the data is to be fetched

    Request body:
      - platform: the name of the platform (eg. google_fit, apple_healthkit, etc.)
      - start_time: the start time of the range (in milliseconds since epoch)
      - end_time: the end time of the range (in milliseconds since epoch)
    """
    key = request.META.get("HTTP_KEY")
    uuid = request.query_params.get("user_uuid")

    try:
        connection = WatchConnection.objects.get(app__key=key, user_uuid=uuid)
    except WatchConnection.DoesNotExist:
        return Response({"error": "Access denied"}, status=401)

    platform = request.data.get("platform")
    start_time = request.data.get("start_time")
    end_time = request.data.get("end_time")

    # try:
    #     start_time = datetime.datetime.fromtimestamp(start_time / 10**3)
    # except Exception:
    #     return Response({"error": "Invalid start time"}, status=400)

    # try:
    #     end_time = datetime.datetime.fromtimestamp(end_time / 10**3)
    # except Exception:
    #     return Response({"error": "Invalid end time"}, status=400)

    # check if any of the above is None and if yes, return error response
    if not all([platform, start_time, end_time]):
        return Response({"error": "Missing parameters"}, status=400)

    if platform == "google_fit":
        # hit GFit APIs for now
        cpm = ConnectedPlatformMetadata.objects.get(
            connection=connection, platform__name="google_fit"
        )
        entries = []
        with GoogleFitConnection(connection.app, cpm) as gfc:
            entries = gfc.get_menstruation_data(
                start_time,
                end_time,
            )

        return Response({"data": entries})
    else:
        return Response({"error": "Platform not supported"}, status=400)


def _show_date_wise_data(connection, platform, data_type):
    fr = datetime.datetime.now() - datetime.timedelta(days=4)
    to = datetime.datetime.now()
    data = {}

    while fr <= to:
        start = datetime.datetime(
            fr.year, fr.month, fr.day, 0, 0, 0, tzinfo=ZoneInfo("Asia/Kolkata")
        )
        end = datetime.datetime(
            fr.year, fr.month, fr.day, 23, 59, 59, tzinfo=ZoneInfo("Asia/Kolkata")
        )
        total = HealthDataEntry.objects.filter(
            user_connection=connection,
            source_platform__name=platform,
            data_type__name=data_type,
            start_time__gte=start,
            end_time__lte=end,
        ).aggregate(Sum("value"))
        data[fr.isoformat()] = total["value__sum"]
        fr += datetime.timedelta(days=1)

    print(data)


def print_synced_uuids():
    # get the unique uuids which have a health data entry object stored
    unique_uuids = (
        HealthDataEntry.objects.all()
        .values_list("user_connection", flat=True)
        .distinct()
    )

    for u in unique_uuids:
        wc = WatchConnection.objects.get(id=u)
        print(wc.user_uuid, wc.app)
