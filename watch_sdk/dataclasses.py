from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass
class FitnessDatatype:
    source: str


@dataclass
class RangeDatatype(FitnessDatatype):
    start_time: int
    end_time: int


@dataclass
class PointDatatype(FitnessDatatype):
    time: int


@dataclass_json
@dataclass
class Steps(RangeDatatype):
    value: int


@dataclass_json
@dataclass
class MoveMinutes(RangeDatatype):
    value: int


@dataclass_json
@dataclass
class CaloriesBurned(RangeDatatype):
    value: float


@dataclass_json
@dataclass
class WaterConsumed(RangeDatatype):
    value: float


@dataclass_json
@dataclass
class CaloriesBMR(RangeDatatype):
    value: float


@dataclass_json
@dataclass
class Weight(PointDatatype):
    value: float


@dataclass_json
@dataclass
class Height(PointDatatype):
    value: float
