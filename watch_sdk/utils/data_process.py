# API layer that processes health data
# - stores it on our server
# - send it to the webhook
# - process for AI model


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
        pass
