"""Constraint Satisfaction Problem (CSP) Solver for Schedule Optimization"""
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from models.activity import ScheduledActivity, ActivityType
from enum import Enum


class Constraint(Enum):
    """Types of constraints"""
    HARD = "hard"  # Must be satisfied
    SOFT = "soft"  # Preferred but can be violated

@dataclass
class TimeSlot:
    """Represents a time slot in a schedule"""
    start_hour: int
    end_hour: int
    day_name: str
    is_available: bool = True
    productivity_factor: float = 1.0  # Productivity multiplier
    
    def overlaps_with(self, other: "TimeSlot") -> bool:
        """Check if two time slots overlap"""
        return self.day_name == other.day_name and not (self.end_hour <= other.start_hour or self.start_hour >= other.end_hour)


class ScheduleOptimizer:
    """Constraint Satisfaction Problem solver for schedule optimization"""
    
    # Time productivity factors (based on typical circadian rhythms)
    PRODUCTIVITY_FACTORS = {
        8: 0.7, 9: 0.8, 10: 0.95, 11: 1.0,      # Morning peak
        12: 0.7, 13: 0.6, 14: 0.7, 15: 0.85,    # Post-lunch dip
        16: 0.9, 17: 0.95, 18: 0.85,             # Afternoon peak
        19: 0.75, 20: 0.8, 21: 0.7, 22: 0.6      # Evening decline
    }
    
    def __init__(self, user_earliest: int = 8, user_latest: int = 22):
        self.user_earliest = user_earliest
        self.user_latest = user_latest
        self.scheduled_activities: List[ScheduledActivity] = []
        self.constraints: List[Tuple[str, callable]] = []
    
    def add_constraint(self, constraint_name: str, constraint_func: callable, is_hard: bool = True):
        """Add a constraint to the CSP"""
        self.constraints.append((constraint_name, constraint_func))
    
    def add_scheduled_activity(self, activity: ScheduledActivity):
        """Add an already-scheduled activity (e.g., class, meeting)"""
        self.scheduled_activities.append(activity)
    
    def get_available_slots(self, duration_minutes: int, num_slots: int = 5) -> List[TimeSlot]:
        """Find available time slots for scheduling"""
        available_slots = []
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        duration_hours = max(duration_minutes / 60, 1)
        
        for day in days:
            for hour in range(self.user_earliest, self.user_latest):
                if hour + duration_hours > self.user_latest:
                    break
                
                slot = TimeSlot(
                    start_hour=hour,
                    end_hour=int(hour + duration_hours),
                    day_name=day,
                    productivity_factor=self.PRODUCTIVITY_FACTORS.get(hour, 0.5)
                )
                
                # Check if slot conflicts with scheduled activities
                if not self._has_conflict(slot):
                    available_slots.append(slot)
        
        # Sort by productivity factor (higher is better)
        available_slots.sort(key=lambda s: s.productivity_factor, reverse=True)
        return available_slots[:num_slots]
    
    def _has_conflict(self, slot: TimeSlot) -> bool:
        """Check if a time slot conflicts with existing activities"""
        for activity in self.scheduled_activities:
            activity_slot = TimeSlot(
                start_hour=activity.start_time.hour,
                end_hour=activity.end_time.hour,
                day_name=activity.start_time.strftime("%A")
            )
            if slot.overlaps_with(activity_slot):
                return True
        return False
    
    def optimize_schedule(self, tasks: List[Dict], num_trials: int = 100) -> List[Dict]:
        """
        Optimize schedule using backtracking with constraint satisfaction

        Returns:
            Optimized schedule with time slots assigned to each task
        """
        best_schedule = None
        best_score = -float('inf')
        
        # Sort tasks by deadline and difficulty (greedy heuristic)
        sorted_tasks = self._sort_tasks(tasks)
        
        for trial in range(num_trials):
            schedule = self._backtrack_schedule(sorted_tasks, [])
            
            if schedule:
                score = self._evaluate_schedule(schedule, sorted_tasks)
                if score > best_score:
                    best_score = score
                    best_schedule = schedule
        
        return best_schedule if best_schedule else self._fallback_schedule(tasks)
    
    def _sort_tasks(self, tasks: List[Dict]) -> List[Dict]:
        """Sort tasks using First-Fit Decreasing (FFD) heuristic"""
        # Priority: deadline urgency > difficulty > duration
        def task_priority(task):
            days_until_deadline = (task.get("deadline", datetime.now() + timedelta(days=7)) - datetime.now()).days
            urgency_score = -days_until_deadline  # Negative so earlier deadlines come first
            difficulty_score = task.get("difficulty", 5)
            duration_score = task.get("duration_min", 60)
            
            return (urgency_score, difficulty_score, duration_score)
        
        return sorted(tasks, key=task_priority)
    
    def _backtrack_schedule(self, tasks: List[Dict], current_schedule: List[Dict]) -> Optional[List[Dict]]:
        """Recursive backtracking to find valid schedule"""
        if not tasks:
            return current_schedule
        
        task = tasks[0]
        available_slots = self.get_available_slots(task["duration_min"], num_slots=3)
        
        for slot in available_slots:
            # Check all constraints
            temp_activity = ScheduledActivity(
                activity_id=f"task_{len(current_schedule)}",
                user_id="temp",
                activity_type=ActivityType.STUDY,
                title=task["subject"],
                start_time=datetime.now().replace(hour=slot.start_hour),
                end_time=datetime.now().replace(hour=slot.end_hour)
            )
            
            # Constraint checking
            if self._satisfies_constraints(temp_activity, current_schedule):
                new_schedule = current_schedule + [{
                    "task": task,
                    "slot": slot,
                    "time_slot": f"{slot.day_name} {slot.start_hour}:00-{slot.end_hour}:00"
                }]
                
                result = self._backtrack_schedule(tasks[1:], new_schedule)
                if result:
                    return result
        
        return None
    
    def _satisfies_constraints(self, activity: ScheduledActivity, schedule: List[Dict]) -> bool:
        """Check if activity satisfies all constraints"""
        for constraint_name, constraint_func in self.constraints:
            if not constraint_func(activity):
                return False
        
        # Built-in constraint: no time overlap
        for scheduled_item in schedule:
            existing_activity = ScheduledActivity(
                activity_id="existing",
                user_id="temp",
                activity_type=ActivityType.STUDY,
                title="existing",
                start_time=datetime.now().replace(hour=scheduled_item["slot"].start_hour),
                end_time=datetime.now().replace(hour=scheduled_item["slot"].end_hour)
            )
            
            if self._has_conflict(TimeSlot(
                start_hour=existing_activity.start_time.hour,
                end_hour=existing_activity.end_time.hour,
                day_name=existing_activity.start_time.strftime("%A")
            )):
                return False
        
        return True
    
    def _evaluate_schedule(self, schedule: List[Dict], tasks: List[Dict]) -> float:
        """Calculate score of a schedule (higher is better)"""
        score = 0.0
        
        for item in schedule:
            slot = item["slot"]
            task = item["task"]
            
            # Productivity factor (place hard tasks during peak hours)
            productivity_bonus = slot.productivity_factor * 10
            
            # Deadline satisfaction (earlier in week for earlier deadlines)
            deadline_bonus = 5 if item.get("time_slot", "").split()[0] != "Sunday" else 2
            
            score += productivity_bonus + deadline_bonus
        
        return score
    
    def _fallback_schedule(self, tasks: List[Dict]) -> List[Dict]:
        """Create a basic schedule if optimization fails"""
        schedule = []
        current_hour = self.user_earliest
        
        for task in tasks:
            duration_hours = max(task["duration_min"] / 60, 1)
            if current_hour + duration_hours > self.user_latest:
                current_hour = self.user_earliest
            
            schedule.append({
                "task": task,
                "time_slot": f"Monday {current_hour}:00-{int(current_hour + duration_hours)}:00"
            })
            current_hour = int(current_hour + duration_hours)
        
        return schedule
