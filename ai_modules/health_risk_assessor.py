"""HealthRiskAssessor — rule-based engine that flags out-of-range health values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HealthWarning:
    """A single flagged risk with severity and remediation guidance."""
    field: str
    severity: str  # "low" | "medium" | "high"
    message: str
    recommendation: str
    value: float | None = None
    threshold: float | None = None


class HealthRiskAssessor:
    """Rule-based risk assessor evaluating BMI, calories, protein, sleep, and hydration."""

    BMI_UNDERWEIGHT = 18.5
    BMI_NORMAL_HIGH = 24.9
    BMI_OVERWEIGHT = 29.9

    CALORIE_DEVIATION_MEDIUM = 0.20
    CALORIE_DEVIATION_HIGH = 0.35
    CALORIE_CONSECUTIVE_DAYS = 3

    PROTEIN_MIN_G_PER_KG = 0.6
    PROTEIN_OPT_G_PER_KG = 0.8

    SLEEP_DEFICIT_HIGH = 6.0
    SLEEP_DEFICIT_MEDIUM = 7.0

    HYDRATION_LOW_THRESHOLD = 0.80

    def __init__(
        self,
        user_profile: Any,
        daily_logs: list[dict],
        activity_logs: list[dict],
        sleep_logs: list[dict] | None = None,
    ) -> None:
        self.profile = user_profile
        self.daily_logs = daily_logs or []
        self.activity_logs = activity_logs or []
        self.sleep_logs = sleep_logs or []

    def assess(self) -> dict[str, Any]:
        """Run all checks and return a structured risk report."""
        warnings: list[dict] = []
        warnings.extend(self.check_bmi())
        warnings.extend(self.check_calorie_deviation())
        warnings.extend(self.check_protein_adequacy())
        warnings.extend(self.check_sleep())
        warnings.extend(self.check_hydration())

        severity_rank = {"high": 0, "medium": 1, "low": 2}
        warnings.sort(key=lambda w: severity_rank.get(w["severity"], 3))

        counts = {s: sum(1 for w in warnings if w["severity"] == s) for s in ("high", "medium", "low")}
        overall = "high" if counts["high"] else ("medium" if counts["medium"] else ("low" if counts["low"] else "none"))

        return {
            "warnings": warnings,
            "total": len(warnings),
            "by_severity": counts,
            "overall_risk": overall,
        }

    def warn(self, field: str, severity: str, message: str, rec: str,
              value: float | None = None, threshold: float | None = None) -> dict:
        w: dict[str, Any] = {"field": field, "severity": severity, "message": message, "recommendation": rec}
        if value is not None:
            w["value"] = value
        if threshold is not None:
            w["threshold"] = threshold
        return w

    def get_nutrient_total(self, log: dict, nutrient: str) -> float | None:
        total, found = 0.0, False
        for meal in log.get("meals", []):
            for item in meal.get("food_items", []):
                info = item.get("nutrition_info") or {}
                if nutrient in info:
                    total += info[nutrient]
                    found = True
        return total if found else None

    def check_bmi(self) -> list[dict]:
        weight = self.profile.current_weight_kg or self.profile.weight_kg
        height_m = self.profile.height_cm / 100.0
        if height_m <= 0:
            return []
        bmi = round(weight / (height_m ** 2), 1)

        if bmi < self.BMI_UNDERWEIGHT:
            return [self.warn("bmi", "medium",
                f"BMI {bmi} is below the healthy range (< {self.BMI_UNDERWEIGHT}).",
                "Consider increasing calorie intake with nutrient-dense foods.", bmi, self.BMI_UNDERWEIGHT)]
        if bmi > self.BMI_OVERWEIGHT:
            return [self.warn("bmi", "high",
                f"BMI {bmi} is in the obese range (> {self.BMI_OVERWEIGHT}).",
                "Focus on a moderate calorie deficit (10–15%) and regular activity.", bmi, self.BMI_OVERWEIGHT)]
        if bmi > self.BMI_NORMAL_HIGH:
            return [self.warn("bmi", "low",
                f"BMI {bmi} is in the overweight range ({self.BMI_NORMAL_HIGH}–{self.BMI_OVERWEIGHT}).",
                "Light calorie reduction combined with strength training can bring BMI back to healthy range.",
                bmi, self.BMI_NORMAL_HIGH)]
        return []

    def check_calorie_deviation(self) -> list[dict]:
        target = self.profile.target_calories
        recent = self.daily_logs[:self.CALORIE_CONSECUTIVE_DAYS]
        if not recent or target <= 0 or len(recent) < self.CALORIE_CONSECUTIVE_DAYS:
            return []

        cals = [self.get_nutrient_total(l, "calories") for l in recent]
        if any(c is None for c in cals):
            return []

        avg_cal = sum(cals) / len(cals)
        deviations = [(c - target) / target for c in cals]

        if all(d > self.CALORIE_DEVIATION_HIGH for d in deviations):
            return [self.warn("calorie_surplus", "high",
                f"Calories have been ≥ {int(self.CALORIE_DEVIATION_HIGH*100)}% above your target ({target} kcal) for {len(recent)} consecutive days (avg {avg_cal:.0f} kcal).",
                "Reduce portion sizes and limit high-calorie snacks.", round(avg_cal, 1), target)]
        if all(d > self.CALORIE_DEVIATION_MEDIUM for d in deviations):
            return [self.warn("calorie_surplus", "medium",
                f"Calories have been ≥ {int(self.CALORIE_DEVIATION_MEDIUM*100)}% above your target for {len(recent)} consecutive days (avg {avg_cal:.0f} kcal).",
                "Monitor portion sizes and reduce calorie-dense foods.", round(avg_cal, 1), target)]
        if all(d < -self.CALORIE_DEVIATION_HIGH for d in deviations):
            return [self.warn("calorie_deficit", "high",
                f"Calories have been ≥ {int(self.CALORIE_DEVIATION_HIGH*100)}% below your target for {len(recent)} consecutive days (avg {avg_cal:.0f} kcal). Severe restriction risks muscle loss.",
                "Increase meal frequency or calorie-dense whole foods.", round(avg_cal, 1), target)]
        if all(d < -self.CALORIE_DEVIATION_MEDIUM for d in deviations):
            return [self.warn("calorie_deficit", "medium",
                f"Calories have been ≥ {int(self.CALORIE_DEVIATION_MEDIUM*100)}% below your target for {len(recent)} consecutive days (avg {avg_cal:.0f} kcal).",
                "A moderate deficit is fine for weight loss, but ensure adequate protein.", round(avg_cal, 1), target)]
        return []

    def check_protein_adequacy(self) -> list[dict]:
        weight = self.profile.current_weight_kg or self.profile.weight_kg
        if weight <= 0 or not self.daily_logs:
            return []

        proteins = [p for p in (self.get_nutrient_total(l, "protein_g") for l in self.daily_logs[:7]) if p is not None]
        if not proteins:
            return []

        avg_p = sum(proteins) / len(proteins)
        min_needed = self.PROTEIN_MIN_G_PER_KG * weight
        opt_needed = self.PROTEIN_OPT_G_PER_KG * weight

        if avg_p < min_needed:
            return [self.warn("protein", "medium",
                f"Average protein intake ({avg_p:.1f} g/day) is below WHO minimum ({min_needed:.1f} g/day).",
                "Add high-protein foods: chicken, fish, eggs, legumes, or Greek yoghurt.", round(avg_p, 1), round(min_needed, 1))]
        if avg_p < opt_needed:
            return [self.warn("protein", "low",
                f"Average protein intake ({avg_p:.1f} g/day) is below wellness recommendation ({opt_needed:.1f} g/day).",
                "Consider adding a protein-rich snack to reach optimal intake.", round(avg_p, 1), round(opt_needed, 1))]
        return []

    def check_sleep(self) -> list[dict]:
        recent = self.sleep_logs[:7]
        durations = [float(l["duration_hours"]) for l in recent if l.get("duration_hours") is not None]
        if not durations:
            return []

        avg_sleep = round(sum(durations) / len(durations), 1)
        if avg_sleep < self.SLEEP_DEFICIT_HIGH:
            return [self.warn("sleep", "high",
                f"Average sleep duration ({avg_sleep:.1f} h) is below {self.SLEEP_DEFICIT_HIGH} h/night over the last {len(durations)} nights.",
                "Prioritise sleep: consistent bedtime, avoid screens and late caffeine.", avg_sleep, self.SLEEP_DEFICIT_HIGH)]
        if avg_sleep < self.SLEEP_DEFICIT_MEDIUM:
            return [self.warn("sleep", "medium",
                f"Average sleep duration ({avg_sleep:.1f} h) is below recommended {self.SLEEP_DEFICIT_MEDIUM} h/night.",
                "Try moving bedtime 30 minutes earlier.", avg_sleep, self.SLEEP_DEFICIT_MEDIUM)]
        return []

    def check_hydration(self) -> list[dict]:
        target_ml = getattr(self.profile, "water_target_ml", 2500)
        recent = self.daily_logs[:7]
        if target_ml <= 0 or not recent:
            return []

        threshold = target_ml * self.HYDRATION_LOW_THRESHOLD
        low_days = sum(1 for l in recent if 0 < (l.get("water_ml") or 0) < threshold)

        if low_days >= 3:
            return [self.warn("hydration", "medium",
                f"Water intake was below 80% of your target ({target_ml} mL) on {low_days} of the last {len(recent)} logged days.",
                "Keep a water bottle visible at your desk and set regular reminders.", float(low_days), threshold)]
        if low_days >= 1:
            return [self.warn("hydration", "low",
                f"Water intake was below 80% of your target on {low_days} recent day(s).",
                "Try to drink a glass of water with each meal and after exercise.", float(low_days), threshold)]
        return []
