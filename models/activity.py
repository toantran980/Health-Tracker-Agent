"""Activity and Study Session Data Models"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ActivityType(Enum):
    """Types of tracked activities"""
    STUDY    = "study"
    EXERCISE = "exercise"
    MEAL     = "meal"
    SLEEP    = "sleep"
    REST     = "rest"
    WORK     = "work"


@dataclass
class ScheduledActivity:
    """A planned activity in the user's calendar."""
    activity_id:   str
    user_id:       str
    activity_type: ActivityType
    title:         str
    start_time:    datetime
    end_time:      datetime
    priority:      int  = 5      # 1-10, higher = more important
    is_recurring:  bool = False
    notes:         str  = ""
    completed:     bool = False

    def get_duration(self) -> int:
        """Return planned duration in minutes."""
        return int((self.end_time - self.start_time).total_seconds() / 60)

    def is_overdue(self, reference: datetime | None = None) -> bool:
        """Return True if the activity end_time has passed and it is not completed."""
        now = reference or datetime.now()
        return not self.completed and self.end_time < now

    def to_dict(self) -> dict:
        return {
            "activity_id":   self.activity_id,
            "user_id":       self.user_id,
            "activity_type": self.activity_type.value,
            "title":         self.title,
            "start_time":    self.start_time.isoformat(),
            "end_time":      self.end_time.isoformat(),
            "duration_min":  self.get_duration(),
            "priority":      self.priority,
            "is_recurring":  self.is_recurring,
            "completed":     self.completed,
        }


@dataclass
class ActivityLog:
    """
    Immutable record of a completed activity used for longitudinal analysis.

    The metadata dict is intentionally open-ended so different activity types
    can store relevant context without requiring schema changes:
        STUDY    → {"subject": "Math", "focus_score": 8}
        EXERCISE → {"type": "run", "distance_km": 5.2}
        MEAL     → {"meal_id": "abc123", "calories": 650}
    """
    log_id:           str
    user_id:          str
    activity_type:    ActivityType
    timestamp:        datetime
    duration_minutes: int
    metadata:         dict = field(default_factory=dict)
    energy_after:     int | None = None   # 1-10 self-reported energy
    notes:            str           = ""

    def to_dict(self) -> dict:
        return {
            "log_id":           self.log_id,
            "user_id":          self.user_id,
            "activity_type":    self.activity_type.value,
            "timestamp":        self.timestamp.isoformat(),
            "duration_minutes": self.duration_minutes,
            "energy_after":     self.energy_after,
            "metadata":         self.metadata,
            "notes":            self.notes,
        }