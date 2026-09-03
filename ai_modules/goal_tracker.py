"""Goal Milestone Tracker — Progress bars and projected completion dates for user health targets."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from models.user_profile import Goal


class GoalTracker:
    """
    Evaluates milestone progress and projected completion dates across active health goals.
    """

    KCAL_PER_KG_FAT = 7700.0  # approximate energy deficit/surplus per kg body mass change

    def __init__(
        self,
        user_profile: Any,            # UserProfile
        daily_logs: list[dict],       # Serialized DailyNutritionLog dicts
        activity_logs: list[dict],    # Serialized ActivityLog dicts
    ):
        self.profile = user_profile
        self.daily_logs = daily_logs or []
        self.activity_logs = activity_logs or []

    def get_milestone_summary(self) -> dict[str, Any]:
        """Compute all active goal milestones, completion percentages, and projections."""
        milestones = []

        # 1. Weight Milestone
        weight_milestone = self.evaluate_weight_goal()
        if weight_milestone:
            milestones.append(weight_milestone)

        # 2. Weekly Exercise Activity Milestone
        exercise_milestone = self.evaluate_exercise_goal()
        if exercise_milestone:
            milestones.append(exercise_milestone)

        # 3. Nutrition Target Adherence Milestone
        nutrition_milestone = self.evaluate_nutrition_adherence_goal()
        if nutrition_milestone:
            milestones.append(nutrition_milestone)

        return {
            "user_id": self.profile.user_id,
            "evaluated_at": datetime.now(timezone.utc).isoformat(),
            "active_goals": [g.value for g in self.profile.goals],
            "milestones": milestones,
            "all_targets_met": all(m["progress_pct"] >= 100.0 for m in milestones) if milestones else False
        }

    def evaluate_weight_goal(self) -> dict[str, Any] | None:
        target_weight = getattr(self.profile, "target_weight_kg", 0.0)
        start_weight = self.profile.weight_kg
        current_weight = self.profile.current_weight_kg or start_weight

        # Check if user has an active weight-related goal
        is_weight_loss = Goal.WEIGHT_LOSS in self.profile.goals
        is_muscle_gain = Goal.MUSCLE_GAIN in self.profile.goals

        if not (is_weight_loss or is_muscle_gain) and target_weight <= 0.0:
            return None

        # If target weight not explicitly specified, infer reasonable target based on goal
        if target_weight <= 0.0:
            if is_weight_loss:
                target_weight = round(start_weight * 0.90, 1)  # default 10% weight loss
            elif is_muscle_gain:
                target_weight = round(start_weight * 1.05, 1)  # default 5% mass gain
            else:
                target_weight = start_weight

        total_change_needed = target_weight - start_weight
        current_change = current_weight - start_weight

        if abs(total_change_needed) < 0.1:
            progress_pct = 100.0
            status = "achieved"
        else:
            raw_progress = (current_change / total_change_needed) * 100.0
            progress_pct = max(0.0, min(100.0, round(raw_progress, 1)))

            if is_weight_loss:
                if current_weight <= target_weight:
                    status = "achieved"
                elif current_weight > start_weight:
                    status = "regressing"
                else:
                    status = "in_progress"
            else:
                if current_weight >= target_weight:
                    status = "achieved"
                elif current_weight < start_weight:
                    status = "regressing"
                else:
                    status = "in_progress"

        # Projected completion date estimation based on average daily calorie deficit/surplus
        projected_date = self.estimate_weight_completion_date(
            current_weight=current_weight,
            target_weight=target_weight,
            is_loss=is_weight_loss
        )

        return {
            "type": "weight",
            "title": "Target Body Weight",
            "start_value": round(start_weight, 1),
            "current_value": round(current_weight, 1),
            "target_value": round(target_weight, 1),
            "unit": "kg",
            "progress_pct": progress_pct,
            "status": status,
            "projected_completion_date": projected_date,
        }

    def estimate_weight_completion_date(
        self, current_weight: float, target_weight: float, is_loss: bool
    ) -> str | None:
        kg_remaining = abs(target_weight - current_weight)
        if kg_remaining < 0.2:
            return datetime.now(timezone.utc).date().isoformat()

        # Compute average daily calorie gap from recent logs
        recent_logs = self.daily_logs[:7]
        target_cal = self.profile.target_calories
        daily_diffs = []
        for log in recent_logs:
            cals = self.log_calories(log)
            if cals > 0 and target_cal > 0:
                daily_diffs.append(target_cal - cals if is_loss else cals - target_cal)

        avg_daily_rate = sum(daily_diffs) / len(daily_diffs) if daily_diffs else (400.0 if is_loss else 300.0)

        # Ensure sensible projection rate
        if avg_daily_rate <= 50.0:
            avg_daily_rate = 300.0  # assume standard healthy deficit/surplus if neutral/stalled

        total_kcal_needed = kg_remaining * self.KCAL_PER_KG_FAT
        days_needed = int(total_kcal_needed / avg_daily_rate)
        # Cap projected days between 1 and 365
        days_needed = max(1, min(365, days_needed))

        proj = datetime.now(timezone.utc) + timedelta(days=days_needed)
        return proj.date().isoformat()

    def evaluate_exercise_goal(self) -> dict[str, Any]:
        target_mins = getattr(self.profile, "weekly_exercise_target_minutes", 150)
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        active_mins = 0
        for act in self.activity_logs:
            try:
                ts_str = act.get("timestamp")
                ts = datetime.fromisoformat(ts_str) if ts_str else None
                if ts and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts and ts < cutoff:
                    continue
            except (ValueError, TypeError):
                continue

            if str(act.get("activity_type", "")).lower() == "exercise":
                active_mins += int(act.get("duration_minutes") or 0)

        progress = min(100.0, round((active_mins / target_mins) * 100.0, 1)) if target_mins > 0 else 100.0

        return {
            "type": "exercise",
            "title": "Weekly Active Exercise",
            "start_value": 0,
            "current_value": active_mins,
            "target_value": target_mins,
            "unit": "minutes/week",
            "progress_pct": progress,
            "status": "achieved" if progress >= 100.0 else "in_progress",
            "projected_completion_date": None
        }

    def evaluate_nutrition_adherence_goal(self) -> dict[str, Any]:
        recent_logs = self.daily_logs[:7]
        target_cals = self.profile.target_calories
        if not recent_logs or target_cals <= 0:
            return {
                "type": "nutrition",
                "title": "Daily Calorie Adherence",
                "start_value": 0,
                "current_value": 0,
                "target_value": 7,
                "unit": "adherent_days/week",
                "progress_pct": 0.0,
                "status": "in_progress",
                "projected_completion_date": None
            }

        adherent_days = 0
        for log in recent_logs:
            cals = self.log_calories(log)
            if abs(cals - target_cals) / target_cals <= 0.15:
                adherent_days += 1

        total_logged = max(len(recent_logs), 1)
        adherence_pct = round((adherent_days / total_logged) * 100.0, 1)

        return {
            "type": "nutrition",
            "title": "Nutrition Target Adherence",
            "start_value": 0,
            "current_value": adherent_days,
            "target_value": total_logged,
            "unit": "days",
            "progress_pct": adherence_pct,
            "status": "achieved" if adherence_pct >= 85.0 else "in_progress",
            "projected_completion_date": None,
        }

    @staticmethod
    def log_calories(log: dict) -> float:
        total = 0.0
        for m in log.get("meals", []):
            for item in m.get("food_items", []):
                total += (item.get("nutrition_info") or {}).get("calories", 0.0)
        return total

