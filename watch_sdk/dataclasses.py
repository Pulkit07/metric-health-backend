from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass
class FitnessDatatype:
    source: str
    start_time: int
    # start time and endtime will be same in case of point datatype
    end_time: int


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
