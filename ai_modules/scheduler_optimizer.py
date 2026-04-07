import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
"""Constraint Satisfaction Problem (CSP) Solver for Schedule Optimization"""
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from models.activity import ScheduledActivity, ActivityType
from enum import Enum
import math


class Constraint(Enum):
    """Types of constraints"""
    HARD = "hard"   # Must be satisfied
    SOFT = "soft"   # Preferred but can be violated


@dataclass
class TimeSlot:
    """Represents a time slot in a schedule"""
    start_hour: float
    end_hour: float
    day_name: str
    is_available: bool = True
    productivity_factor: float = 1.0

    def duration_hours(self) -> float:
        return self.end_hour - self.start_hour

    def overlaps_with(self, other: "TimeSlot") -> bool:
        """Check if two time slots overlap"""
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


class ScheduleOptimizer:
    """Constraint Satisfaction Problem solver for schedule optimization"""

    # Productivity factors based on circadian rhythms (hour → multiplier)
    PRODUCTIVITY_FACTORS = {
        8: 0.70, 9: 0.80, 10: 0.95, 11: 1.00,   # Morning ramp-up / peak
        12: 0.70, 13: 0.60, 14: 0.70, 15: 0.85,  # Post-lunch dip
        16: 0.90, 17: 0.95, 18: 0.85,             # Afternoon peak
        19: 0.75, 20: 0.80, 21: 0.70, 22: 0.60,  # Evening decline
    }

    DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

    def __init__(self, user_earliest: int = 8, user_latest: int = 22):
        self.user_earliest = user_earliest
        self.user_latest = user_latest
        self.scheduled_activities: List[ScheduledActivity] = []
        self.constraints: List[ConstraintEntry] = []

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def add_constraint(self, name: str, func: Callable, is_hard: bool = True):
        """Register a constraint function: func(task, slot) -> bool"""
        ctype = Constraint.HARD if is_hard else Constraint.SOFT
        self.constraints.append(ConstraintEntry(name=name, func=func, ctype=ctype))

    def add_scheduled_activity(self, activity: ScheduledActivity):
        """Block out an already-fixed activity (class, meeting, etc.)"""
        self.scheduled_activities.append(activity)

    def optimize_schedule(self, tasks: List[Dict]) -> List[Dict]:
        """
        Find the best schedule for `tasks` using CSP backtracking.

        Each task dict should contain:
            name         : str
            duration_min : int
            difficulty   : float  (1–10, default 5)
            deadline     : datetime (default +7 days)

        Returns a list of assignment dicts:
            {"task": ..., "slot": TimeSlot, "time_slot": str}
        """
        if not tasks:
            return []

        sorted_tasks = self.sort_tasks(tasks)

        # Pre-compute available slots per task (expensive — do it once)
        slots_cache: Dict[int, List[TimeSlot]] = {
            i: self.get_available_slots(t["duration_min"])
            for i, t in enumerate(sorted_tasks)
        }

        # Map tasks to their index so we can key into the cache
        indexed_tasks = list(enumerate(sorted_tasks))

        result = self.backtrack(indexed_tasks, [], slots_cache)

        if result:
            return self.format_schedule(result)

        # Fallback: greedy linear assignment across the week
        return self.fallback_schedule(sorted_tasks)

    def get_available_slots(self, duration_minutes: int, max_slots: int = 20) -> List[TimeSlot]:
        """
        Return time slots (sorted best-first by productivity) that are free
        and long enough to hold `duration_minutes`.
        """
        duration_hours = duration_minutes / 60  # Preserve fractional hours
        available: List[TimeSlot] = []

        for day in self.DAYS:
            hour = float(self.user_earliest)
            while hour + duration_hours <= self.user_latest:
                slot = TimeSlot(
                    start_hour=hour,
                    end_hour=hour + duration_hours,
                    day_name=day,
                    productivity_factor=self.productivity_at(hour),
                )
                if not self.has_conflict(slot):
                    available.append(slot)
                hour += 0.5  # 30-minute resolution

        available.sort(key=lambda s: s.productivity_factor, reverse=True)
        return available[:max_slots]

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def productivity_at(self, hour: float) -> float:
        """Interpolate productivity for fractional hours."""
        lower = int(math.floor(hour))
        upper = lower + 1
        frac = hour - lower
        p_low = self.PRODUCTIVITY_FACTORS.get(lower, 0.5)
        p_high = self.PRODUCTIVITY_FACTORS.get(upper, 0.5)
        return p_low + frac * (p_high - p_low)

    def has_conflict(self, slot: TimeSlot) -> bool:
        """True if `slot` overlaps any fixed activity."""
        for activity in self.scheduled_activities:
            fixed = TimeSlot(
                start_hour=activity.start_time.hour + activity.start_time.minute / 60,
                end_hour=activity.end_time.hour + activity.end_time.minute / 60,
                day_name=activity.start_time.strftime("%A"),
            )
            if slot.overlaps_with(fixed):
                return True
        return False

    def check_constraints(self, task: Dict, slot: TimeSlot) -> bool:
        """
        Run all registered constraints against a (task, slot) pair.
        Hard constraints must pass; soft constraint failures are ignored here
        (they are handled in scoring).
        """
        for entry in self.constraints:
            if entry.ctype == Constraint.HARD:
                if not entry.func(task, slot):
                    return False
        return True

    def is_valid_assignment(
        self, slot: TimeSlot, current_schedule: List[Dict], task: Dict
    ) -> bool:
        """No overlap with current trial schedule + hard constraints."""
        for item in current_schedule:
            if slot.overlaps_with(item["slot"]):
                return False
        if self.has_conflict(slot):
            return False
        if not self.check_constraints(task, slot):
            return False
        return True

    def backtrack(
        self,
        remaining: List[Tuple[int, Dict]],
        current: List[Dict],
        slots_cache: Dict[int, List[TimeSlot]],
    ) -> Optional[List[Dict]]:
        """
        Recursive CSP backtracking with MRV (Minimum Remaining Values) heuristic.
        remaining : list of (original_index, task_dict) not yet assigned
        current   : assignments so far
        slots_cache: pre-computed candidate slots keyed by original_index
        """
        if not remaining:
            return current  # All tasks assigned

        # MRV: pick the task with fewest valid candidate slots given current schedule
        def mrv_key(idx_task):
            idx, task = idx_task
            return sum(
                1 for s in slots_cache[idx]
                if self.is_valid_assignment(s, current, task)
            )

        idx, task = min(remaining, key=mrv_key)
        next_remaining = [(i, t) for i, t in remaining if i != idx]

        for slot in slots_cache[idx]:
            if self.is_valid_assignment(slot, current, task):
                assignment = {
                    "task": task,
                    "slot": slot,
                }
                result = self.backtrack(next_remaining, current + [assignment], slots_cache)
                if result is not None:
                    return result

        return None  # Dead end — trigger backtrack in caller

    def sort_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """
        Sort tasks by urgency (deadline), then difficulty, then duration.
        Harder + more urgent tasks get first pick of prime time slots.
        """
        now = datetime.now()
        default_deadline = now + timedelta(days=7)

        def priority(task):
            deadline = task.get("deadline", default_deadline)
            days_left = max((deadline - now).total_seconds() / 86400, 0)
            urgency = -days_left                       # Earlier deadline → higher priority
            difficulty = -task.get("difficulty", 5)   # Harder → higher priority
            duration = -task.get("duration_min", 60)  # Longer → schedule first (FFD)
            return (urgency, difficulty, duration)

        return sorted(tasks, key=priority)

    def evaluate_schedule(self, schedule: List[Dict]) -> float:
        """Score a completed schedule (higher = better)."""
        now = datetime.now()
        score = 0.0

        for item in schedule:
            slot: TimeSlot = item["slot"]
            task = item["task"]

            difficulty = task.get("difficulty", 5)
            deadline = task.get("deadline", now + timedelta(days=7))

            # Reward placing hard tasks during productive hours
            productivity_bonus = difficulty * slot.productivity_factor * 5

            # Reward finishing tasks well before their deadline
            slot_dt = self.datetime_for_slot(slot)
            days_buffer = max((deadline - slot_dt).total_seconds() / 86400, 0)
            deadline_bonus = min(days_buffer * 2, 20)   # Cap at 20 pts

            # Small penalty for weekend slots (prefer weekday scheduling)
            weekend_penalty = -3 if slot.day_name in ("Saturday", "Sunday") else 0

            # Soft-constraint satisfaction bonus
            soft_bonus = sum(
                2 for entry in self.constraints
                if entry.ctype == Constraint.SOFT and entry.func(task, slot)
            )

            score += productivity_bonus + deadline_bonus + weekend_penalty + soft_bonus

        return score

    def format_schedule(self, raw: List[Dict]) -> List[Dict]:
        """Attach human-readable time_slot strings and sort by day/time."""
        day_order = {d: i for i, d in enumerate(self.DAYS)}
        for item in raw:
            item["time_slot"] = repr(item["slot"])
        raw.sort(key=lambda x: (day_order[x["slot"].day_name], x["slot"].start_hour))
        return raw

    def fallback_schedule(self, tasks: List[Dict]) -> List[Dict]:
        """
        Greedy linear packing across the week when backtracking finds nothing.
        Iterates days in order and fills slots sequentially.
        """
        schedule = []
        day_cursors = {day: float(self.user_earliest) for day in self.DAYS}

        for task in tasks:
            duration_hours = task["duration_min"] / 60
            placed = False

            for day in self.DAYS:
                cursor = day_cursors[day]
                if cursor + duration_hours <= self.user_latest:
                    slot = TimeSlot(
                        start_hour=cursor,
                        end_hour=cursor + duration_hours,
                        day_name=day,
                        productivity_factor=self.productivity_at(cursor),
                    )
                    if not self.has_conflict(slot):
                        schedule.append({"task": task, "slot": slot, "time_slot": repr(slot)})
                        day_cursors[day] = cursor + duration_hours
                        placed = True
                        break

            if not placed:
                # Truly no room — append with a warning flag
                schedule.append({
                    "task": task,
                    "slot": None,
                    "time_slot": "UNSCHEDULED",
                    "warning": "No available slot found for this task",
                })

        return schedule

    def datetime_for_slot(self, slot: TimeSlot) -> datetime:
        """Convert a TimeSlot into the next real datetime for that day."""
        today = datetime.now()
        target = self.DAYS.index(slot.day_name)
        current = today.weekday()
        days_ahead = (target - current) % 7
        base = today + timedelta(days=days_ahead)
        hour = int(slot.start_hour)
        minute = int((slot.start_hour - hour) * 60)
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)