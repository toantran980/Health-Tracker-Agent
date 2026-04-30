"""Activity and Study Session Data Models"""
from dataclasses import dataclass, field
from typing import Optional, Dict
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
class StudySession:
    """
    Tracks a single study session and derives effectiveness metrics.

    Effectiveness formula
        effectiveness = (focus_score × actual_duration × completion_ratio) / 100

    where completion_ratio = min(actual / planned, 1.0).

    The divisor (max(planned_duration, 1)) guards against ZeroDivisionError
    when planned_duration is accidentally set to 0.
    """
    session_id:        str
    user_id:           str
    subject:           str
    start_time:        datetime
    end_time:          Optional[datetime] = None
    planned_duration:  int               = 60    # minutes
    actual_duration:   Optional[int]     = None  # minutes; set on session end
    focus_score:       Optional[int]     = None  # 1-10 self-reported
    tasks_completed:   int               = 0
    notes:             str               = ""
    difficulty:        int               = 5     # 1-10

    def get_duration(self) -> Optional[int]:
        """
        Compute actual session duration in minutes from timestamps.

        Returns None if the session has not ended yet.
        Prefer actual_duration when set directly (e.g. from a timer widget).
        """
        if self.actual_duration is not None:
            return self.actual_duration
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return None

    def get_effectiveness_score(self) -> float:
        """
        Quantify session effectiveness as a single float.

        Returns 0.0 when either focus_score or duration is unavailable.
        Uses max(planned_duration, 1) to prevent ZeroDivisionError.

        Higher difficulty is not penalised here — it is available as a
        separate signal for downstream analysis (e.g. correlating difficulty
        with focus scores across sessions).
        """
        duration = self.get_duration()
        if not self.focus_score or not duration:
            return 0.0

        completion_ratio = min(duration / max(self.planned_duration, 1), 1.0)
        return round((self.focus_score * duration * completion_ratio) / 100, 4)

    def to_dict(self) -> Dict:
        return {
            "session_id":       self.session_id,
            "user_id":          self.user_id,
            "subject":          self.subject,
            "start_time":       self.start_time.isoformat(),
            "end_time":         self.end_time.isoformat() if self.end_time else None,
            "planned_duration": self.planned_duration,
            "actual_duration":  self.get_duration(),
            "focus_score":      self.focus_score,
            "tasks_completed":  self.tasks_completed,
            "difficulty":       self.difficulty,
            "effectiveness":    self.get_effectiveness_score(),
        }


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

    def is_overdue(self, reference: Optional[datetime] = None) -> bool:
        """Return True if the activity end_time has passed and it is not completed."""
        now = reference or datetime.now()
        return not self.completed and self.end_time < now

    def to_dict(self) -> Dict:
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
    metadata:         Dict = field(default_factory=dict)
    energy_after:     Optional[int] = None   # 1-10 self-reported energy
    notes:            str           = ""

    def to_dict(self) -> Dict:
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