from dataclasses import dataclass
from dataclasses_json import dataclass_json


@dataclass
class FitnessDatatype(frozen=True):
    source: str


@dataclass
class RangeDatatype(FitnessDatatype, frozen=True):
    start_time: int
    end_time: int


@dataclass
class PointDatatype(FitnessDatatype, frozen=True):
    time: int


@dataclass_json
@dataclass
class Steps(RangeDatatype, frozen=True):
    value: int


@dataclass_json
@dataclass
class MoveMinutes(RangeDatatype, frozen=True):
    value: int


@dataclass_json
@dataclass
class CaloriesBurned(RangeDatatype, frozen=True):
    value: float


@dataclass_json
@dataclass
class WaterConsumed(RangeDatatype, frozen=True):
    value: float


@dataclass_json
@dataclass
class CaloriesBMR(RangeDatatype, frozen=True):
    value: float


@dataclass_json
@dataclass
class Weight(PointDatatype, frozen=True):
    value: float


@dataclass_json
@dataclass
class Height(PointDatatype, frozen=True):
    value: float
