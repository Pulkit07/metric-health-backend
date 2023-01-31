from ..dataclasses import *
import typing

RANGE_DATA_TYPES = {
    "com.google.active_minutes": ("move_minutes", MoveMinutes),
    "com.google.step_count.delta": ("steps", Steps),
    "com.google.calories.expended": ("calories", CaloriesBurned),
    "com.google.hydration": ("water_consumed", WaterConsumed),
    "com.google.calories.bmr": ("calories_bmr", CaloriesBMR),
    "com.google.weight": ("weight", Weight),
    "com.google.height": ("height", Height),
    # "com.google.sleep.segment": ("sleep", None),
}

RANGE_DATA_TYPES_ATTRIBUTES: typing.Dict[str, typing.List[str]] = {
    # "com.google.active_minutes": ["merge_active_minutes", "user_input"],
    "com.google.step_count.delta": ["estimated_steps"],
    # "com.google.calories.expended": ["merge_calories_expended", "user_input"],
    # "com.google.hydration": ["merged_hydration", "user_input"],
    # "com.google.calories.bmr": ["merged"],
    # "com.google.weight": ["merge_weight"],
    # "com.google.height": ["merge_height"],
    # "com.google.sleep.segment": ["merged"],
}

RANGE_DATA_TYPES_UNTS: typing.Dict[str, str] = {
    "com.google.active_minutes": "intVal",
    "com.google.step_count.delta": "intVal",
    "com.google.calories.expended": "fpVal",
    "com.google.hydration": "fpVal",
    "com.google.calories.bmr": "fpVal",
    "com.google.weight": "fpVal",
    "com.google.height": "fpVal",
    # "com.google.sleep.segment": "unknown",
}
