from ..dataclasses import *


DB_DATA_TYPE_KEY_MAP = {
    "steps": "steps",
    "water_consumed": "water",
    "calories": "active_energy_burned",
    "height": "height",
    "weight": "weight",
    "blood_glucose": "blood_glucose",
    "blood_oxygen": "blood_oxygen",
    "heart_rate": "heart_rate",
    "sleep": "sleep_analysis",
    # TODO: this should be basal energy burned
    "calories_bmr": None,
    # TODO: figure this out
    "move_minutes": None,
}

DATATYPE_NAME_CLASS_MAP = {
    "height": ("height", Height),
    "weight": ("weight", Weight),
    "active_energy_burned": ("calories", CaloriesBurned),
    "steps": ("steps", Steps),
    "blood_oxygen": ("blood_oxygen", BloodOxygen),
    "heart_rate": ("heart_rate", HeartRate),
    "sleep_analysis": ("sleep", Sleep),
    # "blood_glucose": ("blood_glucose", BloodGlucose),
    # "blood_pressure_diastolic": ("blood_pressure_diastolic", BloodPressureDiastolic),
    # "blood_pressure_systolic": ("blood_pressure_systolic", BloodPressureSystolic),
    # "body_fat_percentage": ("body_fat_percentage", BodyFatPercentage),
    "water": ("water_consumed", WaterConsumed),
    # "body_temperature": ("body_temperature", BodyTemperature),
    # "distance_walking_running": ("distance_walking_running", DistanceWalkingRunning),
    # "body_mass_index": ("body_mass_index", BodyMassIndex),
}
