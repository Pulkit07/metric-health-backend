RANGE_DATA_TYPES = {
    "com.google.active_minutes": "move_minutes",
    "com.google.step_count.delta": "steps",
    "com.google.calories.expended": "calories",
    "com.google.hydration": "water_consumed",
    "com.google.calories.bmr": "calories_bmr",
}

RANGE_DATA_TYPES_ATTRIBUTES = {
    "com.google.active_minutes": ["merge_active_minutes", "user_input"],
    "com.google.step_count.delta": ["estimated_steps", "user_input"],
    "com.google.calories.expended": ["merge_calories_expended", "user_input"],
    "com.google.hydration": ["merged_hydration", "user_input"],
    "com.google.calories.bmr": ["merged"],
}

RANGE_DATA_TYPES_UNTS = {
    "com.google.active_minutes": "intVal",
    "com.google.step_count.delta": "intVal",
    "com.google.calories.expended": "fpVal",
    "com.google.hydration": "fpVal",
    "com.google.calories.bmr": "fpVal",
}

POINT_DATA_TYPES = {
    "com.google.sleep.segment": "sleep",
}

POINT_DATA_TYPES_ATTRIBUTES = {
    "com.google.weight": ["merge_weight"],
    "com.google.sleep.segment": ["merged"],
}

POINT_DATA_TYPES_UNITS = {
    "com.google.weight": "fpVal",
    "com.google.sleep.segment": "unknown",
}
