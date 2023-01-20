from ..dataclasses import *


DATATYPE_NAME_CLASS_MAP = {
    "height": ("height", Height),
    "weight": ("weight", Weight),
    "active_energy_burned": ("calories", CaloriesBurned),
    "steps": ("steps", Steps),
    # "blood_glucose": ("blood_glucose", BloodGlucose),
    # "blood_pressure_diastolic": ("blood_pressure_diastolic", BloodPressureDiastolic),
    # "blood_pressure_systolic": ("blood_pressure_systolic", BloodPressureSystolic),
    # "body_fat_percentage": ("body_fat_percentage", BodyFatPercentage),
    "water": ("water_consumed", WaterConsumed),
    # "heart_rate": ("heart_rate", HeartRate),
    # "blood_oxygen": ("blood_oxygen", BloodOxygen),
    # "body_temperature": ("body_temperature", BodyTemperature),
    # "distance_walking_running": ("distance_walking_running", DistanceWalkingRunning),
    # "body_mass_index": ("body_mass_index", BodyMassIndex),
}
