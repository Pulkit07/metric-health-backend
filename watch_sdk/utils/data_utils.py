from watch_sdk.models import UserData


def save_user_data(connected_platform_meta_data, fitness_data):
    # :todo: WIP, need to enhance this method to make it more generic and error free.
    for data_type, data_type_data in fitness_data:
        objs = [UserData(
            connected_platform_metadata=connected_platform_meta_data,
            data_type=data_type,  # :todo: get the Data type instance
            start_time=data.pop('start_time'),  # :todo: time units to DateTImeField
            end_time=data.pop('end_time'),
            manual_entry=data.pop('manual_entry'),
            device=data.pop('source_device'),
            value=data.pop('value'),
            extra_data=data,  # :todo: need to remove 'source'
            )
            for data in data_type_data
        ]
        UserData.objects.bulk_create(objs)
