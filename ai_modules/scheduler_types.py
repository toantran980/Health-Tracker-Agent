from dataclasses import dataclass
from enum import Enum
from typing import Callable


class Constraint(Enum):
    """Types of constraints used by the scheduler."""

    HARD = "hard"
    SOFT = "soft"


@dataclass
class TimeSlot:
    """Represents a time slot in a schedule."""

    start_hour: float
    end_hour: float
    day_name: str
    is_available: bool = True
    productivity_factor: float = 1.0

    def duration_hours(self) -> float:
        return self.end_hour - self.start_hour

    def overlaps_with(self, other: "TimeSlot") -> bool:
        return (
            self.day_name == other.day_name
            and not (self.end_hour <= other.start_hour or self.start_hour >= other.end_hour)
        )

    def __repr__(self) -> str:
        start = self.fmt(self.start_hour)
        end = self.fmt(self.end_hour)
        return f"{self.day_name} {start}-{end}"

    @staticmethod
    def fmt(hour: float) -> str:
        h = int(hour)
        m = int((hour - h) * 60)
        return f"{h:02d}:{m:02d}"


@dataclass
class ConstraintEntry:
    name: str
    func: Callable
    ctype: Constraint
