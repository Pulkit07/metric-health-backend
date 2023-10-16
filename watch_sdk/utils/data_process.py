# API layer that processes health data
# - stores it on our server
# - send it to the webhook
# - process for AI model


from datetime import datetime
from watch_sdk.models import DataType, HealthDataEntry, Platform
from watch_sdk.utils.webhook import send_data_to_webhook


def process_health_data(fitness_data, watch_connection, user_app, platform_name):
    """
    Process the health data

    :param fitness_data: dict
    :param watch_connection: WatchConnection
    :param user_app: UserApp
    :param platform_name: str
    """
    if user_app.data_storage_option in set(["deny", "both"]):
        send_data_to_webhook(
            fitness_data,
            user_app,
            platform_name,
            watch_connection,
        )

    if user_app.data_storage_option in set(["allow", "both"]):
        # store data on our server
        store_health_data(fitness_data, watch_connection, platform_name)


def store_health_data(fitness_data, watch_connection, platform_name):
    """
    Store the health data on our server

    :param fitness_data: dict
    :param watch_connection: WatchConnection
    :param user_app: UserApp
    :param platform_name: str
    """
    to_create = []
    platform_obj = Platform.objects.get(name=platform_name)
    for data_type, entries in fitness_data.items():
        data_type_obj = DataType.objects.get(name=data_type)
        for entry in entries:
            entry.pop("source")
            to_create.append(
                HealthDataEntry(
                    user_connection=watch_connection,
                    source_platform=platform_obj,
                    data_type=data_type_obj,
                    start_time=datetime.fromtimestamp(
                        entry.pop("start_time") / 10**3
                    ),
                    end_time=datetime.fromtimestamp(entry.pop("end_time") / 10**3),
                    manual_entry=entry.pop("manual_entry", False),
                    value=entry.pop("value"),
                    source_device=entry.pop("source_device", None),
                    extra_data=entry,
                )
            )

    HealthDataEntry.objects.bulk_create(to_create)
