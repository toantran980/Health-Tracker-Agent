"""Weekly Digest Generator — Comprehensive multi-domain weekly health and productivity summary."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from ai_modules.goal_tracker import GoalTracker
from ai_modules.health_risk_assessor import HealthRiskAssessor


class WeeklyDigestGenerator:
    """
    Synthesizes data across nutrition, activity, sleep, goals, and health risks
    into an executive weekly report with automated natural-language highlights.
    """

    def __init__(
        self,
        user_profile: Any,            # UserProfile
        daily_logs: list[dict],       # Serialized DailyNutritionLog dicts
        activity_logs: list[dict],    # Serialized ActivityLog dicts
        sleep_logs: list[dict] | None = None,
    ):
        self.profile = user_profile
        self.daily_logs = daily_logs or []
        self.activity_logs = activity_logs or []
        self.sleep_logs = sleep_logs or []

    def generate(self) -> dict[str, Any]:
        """Generate the full weekly digest document."""
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=7)

        # 1. Nutrition summary
        nutrition_summary = self.summarize_nutrition()

        # 2. Activity summary
        activity_summary = self.summarize_activity(start_date)

        # 3. Sleep summary
        sleep_summary = self.summarize_sleep()

        # 4. Goals & milestones
        tracker = GoalTracker(self.profile, self.daily_logs, self.activity_logs)
        goal_summary = tracker.get_milestone_summary()

        # 5. Health risks
        assessor = HealthRiskAssessor(self.profile, self.daily_logs, self.activity_logs, self.sleep_logs)
        risk_summary = assessor.assess()

        # 6. Highlights & action points
        highlights = self.generate_highlights(
            nutrition_summary, activity_summary, sleep_summary, goal_summary, risk_summary
        )

        return {
            "user_id": self.profile.user_id,
            "period": {
                "start": start_date.date().isoformat(),
                "end": now.date().isoformat(),
                "generated_at": now.isoformat(),
            },
            "highlights": highlights,
            "nutrition": nutrition_summary,
            "activity": activity_summary,
            "sleep": sleep_summary,
            "goals": goal_summary.get("milestones", []),
            "health_risks": {
                "total_warnings": risk_summary.get("total", 0),
                "overall_risk": risk_summary.get("overall_risk", "none"),
                "warnings": risk_summary.get("warnings", []),
            },
        }

    def summarize_nutrition(self) -> dict[str, Any]:
        recent = self.daily_logs[:7]
        if not recent:
            return {
                "days_logged": 0,
                "avg_calories": 0.0,
                "avg_protein_g": 0.0,
                "avg_carbs_g": 0.0,
                "avg_fat_g": 0.0,
                "target_calories": self.profile.target_calories,
            }

        totals = {"calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0}
        for log in recent:
            for meal in log.get("meals", []):
                for item in meal.get("food_items", []):
                    info = item.get("nutrition_info") or {}
                    for k in totals:
                        totals[k] += info.get(k, 0.0)

        n_days = max(len(recent), 1)
        return {
            "days_logged": len(recent),
            "avg_calories": round(totals["calories"] / n_days, 1),
            "avg_protein_g": round(totals["protein_g"] / n_days, 1),
            "avg_carbs_g": round(totals["carbs_g"] / n_days, 1),
            "avg_fat_g": round(totals["fat_g"] / n_days, 1),
            "target_calories": self.profile.target_calories,
        }


    def summarize_activity(self, cutoff: datetime) -> dict[str, Any]:
        by_type: dict[str, int] = {}
        total_minutes = 0
        energy_scores: list[float] = []

        for log in self.activity_logs:
            try:
                ts_str = log.get("timestamp")
                ts = datetime.fromisoformat(ts_str) if ts_str else None
                if ts and ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
                if ts and ts < cutoff:
                    continue
            except (ValueError, TypeError):
                continue

            act_type = str(log.get("activity_type", "unknown")).lower()
            mins = int(log.get("duration_minutes") or 0)
            by_type[act_type] = by_type.get(act_type, 0) + mins
            total_minutes += mins

            energy = log.get("energy_after")
            if energy is not None:
                try:
                    energy_scores.append(float(energy))
                except (ValueError, TypeError):
                    pass

        return {
            "total_active_minutes": total_minutes,
            "minutes_by_type": by_type,
            "avg_energy_after": round(sum(energy_scores) / len(energy_scores), 1) if energy_scores else None,
            "workout_minutes": by_type.get("exercise", 0),
            "study_minutes": by_type.get("study", 0),
        }

    def summarize_sleep(self) -> dict[str, Any]:
        recent = self.sleep_logs[:7]
        if not recent:
            return {
                "nights_logged": 0,
                "avg_duration_hours": None,
                "avg_quality_score": None,
            }

        durations = [float(l["duration_hours"]) for l in recent if l.get("duration_hours") is not None]
        qualities = [float(l["quality_score"]) for l in recent if l.get("quality_score") is not None]

        return {
            "nights_logged": len(recent),
            "avg_duration_hours": round(sum(durations) / len(durations), 1) if durations else None,
            "avg_quality_score": round(sum(qualities) / len(qualities), 1) if qualities else None,
        }

    def generate_highlights(
        self,
        nutrition: dict[str, Any],
        activity: dict[str, Any],
        sleep: dict[str, Any],
        goals: dict[str, Any],
        risks: dict[str, Any],
    ) -> list[str]:
        items: list[str] = []

        # Nutrition highlight
        if nutrition["days_logged"] > 0:
            cal_diff = nutrition["avg_calories"] - nutrition["target_calories"]
            if abs(cal_diff) <= 150:
                items.append(f"Nutrition consistency on track: averaged {nutrition['avg_calories']} kcal/day.")
            elif cal_diff > 150:
                items.append(f"Calorie surplus: averaged {nutrition['avg_calories']} kcal/day ({int(cal_diff)} above target).")
            else:
                items.append(f"Calorie deficit: averaged {nutrition['avg_calories']} kcal/day ({int(abs(cal_diff))} below target).")

        # Exercise highlight
        workout_mins = activity.get("workout_minutes", 0)
        if workout_mins >= 150:
            items.append(f"Met weekly WHO exercise benchmark with {workout_mins} active workout minutes.")
        elif workout_mins > 0:
            items.append(f"Logged {workout_mins} minutes of workouts this week.")

        # Sleep highlight
        if sleep["avg_duration_hours"] is not None:
            if sleep["avg_duration_hours"] >= 7.0:
                items.append(f"Solid sleep duration: averaged {sleep['avg_duration_hours']} hours per night.")
            else:
                items.append(f"Sleep deficit noted: averaged only {sleep['avg_duration_hours']} hours per night.")

        # Health risk highlight
        warn_count = risks.get("total_warnings", 0)
        if warn_count > 0:
            items.append(f"{warn_count} health advisory flag(s) identified — review the Health Risks section.")
        else:
            items.append("Zero high-severity health anomalies detected this week.")

        return items
