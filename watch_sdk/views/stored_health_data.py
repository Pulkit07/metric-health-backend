# APIs to return health data stored on our servers

import datetime
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum

from watch_sdk.models import HealthDataEntry, UserApp, WatchConnection
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

    try:
        start_time = datetime.datetime.fromtimestamp(start_time / 10**3)
    except Exception:
        return Response({"error": "Invalid start time"}, status=400)

    try:
        end_time = datetime.datetime.fromtimestamp(end_time / 10**3)
    except Exception:
        return Response({"error": "Invalid end time"}, status=400)

    # check if any of the above is None and if yes, return error response
    if not all([platform, data_type, start_time, end_time]):
        return Response({"error": "Missing parameters"}, status=400)

    total = HealthDataEntry.objects.filter(
        user_connection=connection,
        source_platform__name=platform,
        data_type__name=data_type,
        start_time__gte=start_time,
        end_time__lte=end_time,
    ).aggregate(Sum("value"))

    return Response({"total": total["value__sum"]})


def test_function():
    pass
    # get the unique uuids which have a health data entry object stored
    # unique_uuids = (
    #     HealthDataEntry.objects.all()
    #     .values_list("user_connection", flat=True)
    #     .distinct()
    # )

    # for u in unique_uuids:
    #     wc = WatchConnection.objects.get(id=u)
    #     print(wc.user_uuid, wc.app)
