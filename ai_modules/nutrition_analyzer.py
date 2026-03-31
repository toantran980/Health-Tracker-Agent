import math
from typing import List, Dict, Optional
from models.meal import DailyNutritionLog, NutritionInfo


class NutritionAnalyzer:
    """Statistical pattern recognition and nutritional analysis"""

    def __init__(self, target_nutrition: NutritionInfo):
        self.target_nutrition = target_nutrition
        self.history: List[DailyNutritionLog] = []

    # ------------------------------------------------------------------ #
    #  Data ingestion                                                       #
    # ------------------------------------------------------------------ #

    def add_daily_log(self, log: DailyNutritionLog) -> None:
        """Append a daily nutrition log to history."""
        self.history.append(log)

    # ------------------------------------------------------------------ #
    #  Vector helpers                                                       #
    # ------------------------------------------------------------------ #

    def _to_vector(self, info: NutritionInfo) -> List[float]:
        """Return a 4-D macro vector: [calories, protein_g, carbs_g, fat_g]."""
        return [info.calories, info.protein_g, info.carbs_g, info.fat_g]

    def _normalize_vector(self, vec: List[float]) -> List[float]:
        """L2-normalise a vector so cosine similarity is scale-independent."""
        magnitude = math.sqrt(sum(v ** 2 for v in vec))
        return [v / magnitude for v in vec] if magnitude > 0 else vec

    def _cosine_similarity(self, a: NutritionInfo, b: NutritionInfo) -> float:
        """
        Cosine similarity between two NutritionInfo objects in 4-D macro space.

        Both vectors are L2-normalised first so that no single macro
        (e.g. calories ~2 000 vs fat ~60 g) dominates the result.

        Returns a value in [0, 1] where 1 means identical macro ratios.
        """
        va = self._normalize_vector(self._to_vector(a))
        vb = self._normalize_vector(self._to_vector(b))
        return sum(x * y for x, y in zip(va, vb))

    # ------------------------------------------------------------------ #
    #  Core statistics                                                      #
    # ------------------------------------------------------------------ #

    def get_weekly_average(self, days: int = 7) -> NutritionInfo:
        """Return average nutrition over the most recent *days* logs."""
        if not self.history:
            return NutritionInfo(0, 0, 0, 0)

        recent = self.history[-days:]
        n = len(recent)
        totals = [log.get_total_nutrition() for log in recent]

        return NutritionInfo(
            calories=sum(t.calories  for t in totals) / n,
            protein_g=sum(t.protein_g for t in totals) / n,
            carbs_g=sum(t.carbs_g   for t in totals) / n,
            fat_g=sum(t.fat_g     for t in totals) / n,
        )

    def calculate_adherence_rate(self, days: int = 7) -> float:
        """
        Percentage of recent days whose total nutrition sat within 90 % of
        every macro target simultaneously.
        """
        if not self.history:
            return 0.0
        recent = self.history[-days:]
        adherent = sum(
            1 for log in recent
            if log.get_adherence_ratio(self.target_nutrition) >= 0.9
        )
        return (adherent / len(recent)) * 100

    # ------------------------------------------------------------------ #
    #  Anomaly detection (Z-score, holdout baseline)                        #
    # ------------------------------------------------------------------ #

    def detect_nutritional_anomalies(self, sensitivity: float = 2.0) -> List[Dict]:
        """
        Track B — Statistical Anomaly Detection via Z-Score.

        The mean and standard deviation are derived exclusively from *older*
        history (everything before the last 7 days) so that an anomalous day
        cannot pull the baseline toward itself — a classic statistical error
        present in naive implementations.

        Requires at least 10 total log entries (>= 3 baseline days).
        """
        if len(self.history) < 10:
            return []

        baseline_logs = self.history[:-7]
        recent_logs   = self.history[-7:]

        baseline_cals = [log.get_total_nutrition().calories for log in baseline_logs]
        mean  = sum(baseline_cals) / len(baseline_cals)
        std   = math.sqrt(sum((c - mean) ** 2 for c in baseline_cals) / len(baseline_cals))

        if std == 0:
            return []

        anomalies = []
        for log in recent_logs:
            cal = log.get_total_nutrition().calories
            z   = (cal - mean) / std
            if abs(z) > sensitivity:
                anomalies.append({
                    "date":      log.date,
                    "calories":  round(cal, 1),
                    "z_score":   round(abs(z), 2),
                    "direction": "over" if z > 0 else "under",
                })
        return anomalies

    # ------------------------------------------------------------------ #
    #  Meal pattern recognition                                             #
    # ------------------------------------------------------------------ #

    def identify_meal_patterns(self) -> Dict:
        """
        Identify recurring food items and average meal-timing hours.

        Returns:
            Dict with keys:
              - favorite_meals: top-5 foods by frequency
              - meal_timing: average hour of day per meal type
              - macro_preferences: 'high_protein' | 'high_carb' | 'balanced'
        """
        meal_counts: Dict[str, int]   = {}
        meal_hours:  Dict[str, List[int]] = {}

        for log in self.history:
            for meal in log.meals:
                meal_type = meal.meal_type.value

                # Frequency counting
                for food in meal.food_items:
                    meal_counts[food.name] = meal_counts.get(food.name, 0) + 1

                # Timing
                meal_hours.setdefault(meal_type, []).append(meal.timestamp.hour)

        top_meals    = dict(sorted(meal_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        avg_timing   = {mt: round(sum(hours) / len(hours)) for mt, hours in meal_hours.items()}

        return {
            "favorite_meals":   top_meals,
            "meal_timing":      avg_timing,
            "macro_preferences": self._get_macro_pref(),
        }

    def _get_macro_pref(self) -> str:
        """Classify the user's dominant macro preference from recent averages."""
        macros = self.get_weekly_average().get_macro_ratio()
        if macros["protein_percent"] > 35:
            return "high_protein"
        if macros["carbs_percent"] > 55:
            return "high_carb"
        return "balanced"

    # ------------------------------------------------------------------ #
    #  Macro recommendations                                               #
    # ------------------------------------------------------------------ #

    def get_macro_recommendations(self, goal: Optional[str] = None) -> Dict[str, str]:
        """
        Goal-aware macro recommendations.

        Goal-specific weights shift which nutrient gap is treated as most
        urgent (Track B — reasoning adapts to user context).
        """
        GOAL_WEIGHTS = {
            "MUSCLE_GAIN": {"protein": 0.6, "carbs": 0.2, "fat": 0.2},
            "WEIGHT_LOSS": {"protein": 0.3, "carbs": 0.5, "fat": 0.2},
            None:           {"protein": 0.34, "carbs": 0.33, "fat": 0.33},
        }
        weights = GOAL_WEIGHTS.get(goal, GOAL_WEIGHTS[None])

        recent_avg    = self.get_weekly_average(7)
        target_macros = self.target_nutrition.get_macro_ratio()
        recent_macros = recent_avg.get_macro_ratio()

        recommendations: Dict[str, str] = {}
        macro_map = {
            "protein": ("protein_percent", "protein"),
            "carbs":   ("carbs_percent",   "carbs"),
            "fat":     ("fat_percent",     "fat"),
        }

        for key, (pct_key, label) in macro_map.items():
            current = recent_macros[pct_key]
            target  = target_macros[pct_key]
            gap     = current - target
            # Scale the acceptable tolerance inversely with goal weight —
            # high-priority macros get a tighter ±3 % band, others ±5 %.
            tolerance = 3.0 if weights[key] >= 0.5 else 5.0

            if gap < -tolerance:
                recommendations[key] = (
                    f"Increase {label}: currently {current:.1f} %, "
                    f"target {target:.1f} % (priority weight {weights[key]:.0%})"
                )
            elif gap > tolerance:
                recommendations[key] = (
                    f"Reduce {label}: currently {current:.1f} %, "
                    f"target {target:.1f} % (priority weight {weights[key]:.0%})"
                )
            else:
                recommendations[key] = f"{label.capitalize()} intake is on target ✓"

        return recommendations

    # ------------------------------------------------------------------ #
    #  Pearson correlation — diet adherence vs. performance                #
    # ------------------------------------------------------------------ #

    def correlate_nutrition_performance(self, focus_scores: List[int]) -> float:
        """
        Pearson r between daily diet-adherence ratio and external focus scores.
        """
        if len(self.history) < 2 or len(focus_scores) != len(self.history):
            return 0.0

        adherence = [
            log.get_adherence_ratio(self.target_nutrition)
            for log in self.history
        ]
        return self._pearson_correlation(adherence, [float(s) for s in focus_scores])

    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Standard Pearson correlation coefficient."""
        n = len(x)
        if n < 2 or len(y) != n:
            return 0.0

        mu_x = sum(x) / n
        mu_y = sum(y) / n
        num  = sum((x[i] - mu_x) * (y[i] - mu_y) for i in range(n))
        den  = math.sqrt(
            sum((xi - mu_x) ** 2 for xi in x) *
            sum((yi - mu_y) ** 2 for yi in y)
        )
        return num / den if den != 0 else 0.0

    @staticmethod
    def interpret_correlation(r: float) -> str:
        """Translate a Pearson r value into a plain-English insight."""
        direction = "positive" if r >= 0 else "negative"
        abs_r = abs(r)
        if abs_r >= 0.7:
            strength = "Strong"
        elif abs_r >= 0.4:
            strength = "Moderate"
        elif abs_r >= 0.2:
            strength = "Weak"
        else:
            return f"No meaningful relationship detected (r = {r:.2f})."
        return (
            f"{strength} {direction} relationship between diet adherence and "
            f"focus performance (r = {r:.2f})."
        )

    # ------------------------------------------------------------------ #
    #  Weighted adherence score (goal-aware, used by report)               #
    # ------------------------------------------------------------------ #

    def weighted_adherence_score(self, log: DailyNutritionLog, goal: Optional[str] = None) -> float:
        """
        Return a [0, 1] adherence score for a single day, weighted by goal.

        Each macro is scored as 1 − normalised absolute deviation from target,
        then combined using goal-specific weights so the metric actually
        changes meaning with the user's objective (Track B reasoning).
        """
        GOAL_WEIGHTS = {
            "MUSCLE_GAIN": {"calories": 0.2, "protein": 0.6, "carbs": 0.1, "fat": 0.1},
            "WEIGHT_LOSS": {"calories": 0.5, "protein": 0.3, "carbs": 0.1, "fat": 0.1},
            None:           {"calories": 0.25, "protein": 0.25, "carbs": 0.25, "fat": 0.25},
        }
        weights = GOAL_WEIGHTS.get(goal, GOAL_WEIGHTS[None])
        actual  = log.get_total_nutrition()
        target  = self.target_nutrition

        def _fit(actual_val: float, target_val: float) -> float:
            if target_val == 0:
                return 1.0
            return max(0.0, 1.0 - abs(actual_val - target_val) / target_val)

        return (
            weights["calories"] * _fit(actual.calories,  target.calories)  +
            weights["protein"]  * _fit(actual.protein_g, target.protein_g) +
            weights["carbs"]    * _fit(actual.carbs_g,   target.carbs_g)   +
            weights["fat"]      * _fit(actual.fat_g,     target.fat_g)
        )

    # ------------------------------------------------------------------ #
    #  Comprehensive report                                                 #
    # ------------------------------------------------------------------ #

    def get_nutrition_report(
        self,
        goal: Optional[str] = None,
        focus_scores: Optional[List[int]] = None,
    ) -> Dict:
        """
        Generate a comprehensive nutrition report

        Returns:
            Nested dict with averages, adherence, anomalies, patterns,
            recommendations, and (optionally) performance correlation.
        """
        avg = self.get_weekly_average()

        report: Dict = {
            "weekly_average": {
                "calories":  round(avg.calories,  1),
                "protein_g": round(avg.protein_g, 1),
                "carbs_g":   round(avg.carbs_g,   1),
                "fat_g":     round(avg.fat_g,     1),
            },
            "macro_similarity_to_target": round(
                self._cosine_similarity(avg, self.target_nutrition), 4
            ),
            "adherence_rate_pct":  round(self.calculate_adherence_rate(), 1),
            "anomalies":           self.detect_nutritional_anomalies(),
            "patterns":            self.identify_meal_patterns(),
            "recommendations":     self.get_macro_recommendations(goal),
        }

        # Performance correlation block — only included when scores provided
        if focus_scores:
            r = self.correlate_nutrition_performance(focus_scores)
            report["performance_correlation"] = {
                "r":         round(r, 4),
                "insight":   self.interpret_correlation(r),
            }

        return report
