"""Activity and Study Session Data Models"""
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime
from enum import Enum


class ActivityType(Enum):
    """Types of activities"""
    STUDY = "study"
    EXERCISE = "exercise"
    MEAL = "meal"
    SLEEP = "sleep"
    REST = "rest"
    WORK = "work"


@dataclass
class StudySession:
    """Study session tracking"""
    session_id: str
    user_id: str
    subject: str
    start_time: datetime
    end_time: Optional[datetime] = None
    planned_duration: int = 60  # minutes
    actual_duration: Optional[int] = None
    focus_score: Optional[int] = None  # 1-10 self-reported focus level
    tasks_completed: int = 0
    notes: str = ""
    difficulty: int = 5  # 1-10 scale, difficulty of task
    
    def get_duration(self) -> Optional[int]:
        """Calculate actual session duration in minutes"""
        if self.end_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return None
    
    def get_effectiveness_score(self) -> float:
        """Calculate study session effectiveness"""
        if not self.focus_score or not self.actual_duration:
            return 0.0
        # Effectiveness = (Focus Score × Duration × Completion Ratio) / 100
        completion_ratio = min(self.actual_duration / self.planned_duration, 1.0)
        return (self.focus_score * self.actual_duration * completion_ratio) / 100


@dataclass
class ScheduledActivity:
    """Planned activity in calendar"""
    activity_id: str
    user_id: str
    activity_type: ActivityType
    title: str
    start_time: datetime
    end_time: datetime
    priority: int = 5  # 1-10, higher is more important
    is_recurring: bool = False
    notes: str = ""
    completed: bool = False
    
    def get_duration(self) -> int:
        """Get duration in minutes"""
        return int((self.end_time - self.start_time).total_seconds() / 60)


@dataclass
class ActivityLog:
    """Log of completed activity for analysis"""
    log_id: str
    user_id: str
    activity_type: ActivityType
    timestamp: datetime
    duration_minutes: int
    metadata: dict = field(default_factory=dict)
    energy_after: Optional[int] = None
    notes: str = ""
