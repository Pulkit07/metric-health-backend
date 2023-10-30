from dataclasses import dataclass
from dataclasses_json import dataclass_json
from typing import Optional


@dataclass
class FitnessDatatype:
    # this is name of platform like google_fit, apple_healthkit, strava, etc
    source: str
    start_time: int
    # start time and endtime will be same in case of point datatype
    end_time: int
    # whether this data was entered manually or not
    manual_entry: bool
    # this is name of device that recorded this data, mostly used for apple_healthkit
    source_device: Optional[str]


@dataclass_json
@dataclass
class Steps(FitnessDatatype):
    value: int


@dataclass_json
@dataclass
class MoveMinutes(FitnessDatatype):
    value: int


@dataclass_json
@dataclass
class DistanceMoved(FitnessDatatype):
    value: float


@dataclass_json
@dataclass
class CaloriesBurned(FitnessDatatype):
    value: float


@dataclass_json
@dataclass
class WaterConsumed(FitnessDatatype):
    value: float


@dataclass_json
@dataclass
class CaloriesBMR(FitnessDatatype):
    value: float


@dataclass_json
@dataclass
class Weight(FitnessDatatype):
    value: float


@dataclass_json
@dataclass
class Height(FitnessDatatype):
    value: float


@dataclass_json
@dataclass
class BloodOxygen(FitnessDatatype):
    value: float


@dataclass_json
@dataclass
class HeartRate(FitnessDatatype):
    value: float


@dataclass_json
@dataclass
class Sleep(FitnessDatatype):
    # sleep_type can be one of the following:
    # "awake", "light", "deep", "rem"
    sleep_type: str
    # duration in milliseconds
    value: int


@dataclass_json
@dataclass
class StravaCycling(FitnessDatatype):
    # strava specific activity id
    activity_id: int
    distance: float
    moving_time: int
    max_speed: float
    average_speed: float
    total_elevation_gain: float


@dataclass_json
@dataclass
class StravaRun(FitnessDatatype):
    # strava specific activity id
    activity_id: int
    distance: float
    moving_time: int
    max_speed: float
    average_speed: float
    total_elevation_gain: float


@dataclass_json
@dataclass
class StravaWalk(FitnessDatatype):
    # strava specific activity id
    activity_id: int
    distance: float
    moving_time: int
    max_speed: float
    average_speed: float
    total_elevation_gain: float
