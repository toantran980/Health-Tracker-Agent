"""User Profile Data Model"""
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime
from enum import Enum


class Goal(Enum):
    """User health goals"""
    WEIGHT_LOSS          = "weight_loss"
    MUSCLE_GAIN          = "muscle_gain"
    ENERGY_OPTIMIZATION  = "energy_optimization"
    GENERAL_WELLNESS     = "general_wellness"


class BiologicalSex(Enum):
    """
    Biological sex used exclusively for BMR calculation.

    The Mifflin-St Jeor equation uses different constants for males (+5)
    and females (−161).  Without this field the formula always returns male
    values, producing incorrect TDEE estimates for ~50 % of users.
    """
    MALE   = "male"
    FEMALE = "female"


@dataclass
class UserProfile:
    """Comprehensive user profile for health and study tracking."""

    # ------------------------------------------------------------------ #
    #  Identity                                                             #
    # ------------------------------------------------------------------ #
    user_id:    str
    name:       str
    age:        int
    weight_kg:  float
    height_cm:  float
    biological_sex: BiologicalSex = BiologicalSex.MALE   # affects BMR formula

    # ------------------------------------------------------------------ #
    #  Health goals                                                         #
    # ------------------------------------------------------------------ #
    goals: List[Goal] = field(default_factory=lambda: [Goal.GENERAL_WELLNESS])

    # ------------------------------------------------------------------ #
    #  Dietary preferences                                                  #
    # ------------------------------------------------------------------ #
    dietary_restrictions: List[str] = field(default_factory=list)  # "vegan", "gluten_free", …
    allergies:            List[str] = field(default_factory=list)
    preferred_cuisine:    List[str] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    #  Daily nutritional targets                                            #
    # ------------------------------------------------------------------ #
    target_calories:  int   = 2000
    target_protein_g: float = 50.0
    target_carbs_g:   float = 250.0
    target_fat_g:     float = 65.0

    # ------------------------------------------------------------------ #
    #  Study / work schedule preferences                                    #
    # ------------------------------------------------------------------ #
    work_hours_per_day:           int = 8
    study_hours_per_day:          int = 2
    max_study_session_duration:   int = 120   # minutes
    min_study_session_duration:   int = 25    # minutes
    earliest_study_time:          int = 8     # 24-hour clock
    latest_study_time:            int = 22    # 24-hour clock

    # ------------------------------------------------------------------ #
    #  Current metrics                                                      #
    # ------------------------------------------------------------------ #
    current_sleep_hours:  float = 8.0
    current_energy_level: int   = 5    # 1-10 scale
    current_weight_kg:    float = 0.0  # initialised in __post_init__

    # ------------------------------------------------------------------ #
    #  Behavioural history                                                  #
    # ------------------------------------------------------------------ #
    daily_logs: List[Dict] = field(default_factory=list)
    created_at: datetime   = field(default_factory=datetime.now)

    # ------------------------------------------------------------------ #
    #  Post-init                                                            #
    # ------------------------------------------------------------------ #
    def __post_init__(self) -> None:
        if self.current_weight_kg == 0.0:
            self.current_weight_kg = self.weight_kg

    # ------------------------------------------------------------------ #
    #  Physiological calculations                                           #
    # ------------------------------------------------------------------ #
    def get_bmr(self) -> float:
        """
        Basal Metabolic Rate via the Mifflin-St Jeor equation.

        Male:   BMR = 10W + 6.25H − 5A + 5
        Female: BMR = 10W + 6.25H − 5A − 161

        where W = weight (kg), H = height (cm), A = age (years).

        For users under 18 a simplified weight-scaling formula is used
        because Mifflin-St Jeor was validated on adults only.
        """
        if self.age < 18:
            return self.weight_kg * 20.0

        base = 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age
        offset = 5 if self.biological_sex == BiologicalSex.MALE else -161
        return base + offset

    def get_tdee(self, activity_level: float = 1.5) -> int:
        """
        Total Daily Energy Expenditure = BMR × activity multiplier.

        Common multipliers:
            1.2  — sedentary (desk job, little exercise)
            1.375 — lightly active (1-3 days/week exercise)
            1.55  — moderately active (3-5 days/week)
            1.725 — very active (6-7 days/week hard training)
            1.9   — extra active (physical job + training)

        Args:
            activity_level: Harris-Benedict activity multiplier.

        Returns:
            Rounded TDEE in kcal/day.
        """
        if activity_level <= 0:
            raise ValueError("activity_level must be positive.")
        return int(self.get_bmr() * activity_level)

    def get_recommended_targets(self, activity_level: float = 1.5) -> Dict[str, float]:
        """
        Derive evidence-based daily macro targets from TDEE and active goals.

        Macro splits used:
            MUSCLE_GAIN      — protein 30 %, carbs 50 %, fat 20 %
            WEIGHT_LOSS      — protein 35 %, carbs 35 %, fat 30 %
            ENERGY_OPTIMIZATION / GENERAL_WELLNESS — protein 25 %, carbs 50 %, fat 25 %

        When multiple goals are active the first recognised goal wins.

        Returns:
            Dict with keys: calories, protein_g, carbs_g, fat_g.
        """
        tdee = self.get_tdee(activity_level)

        if Goal.MUSCLE_GAIN in self.goals:
            protein_pct, carbs_pct, fat_pct = 0.30, 0.50, 0.20
        elif Goal.WEIGHT_LOSS in self.goals:
            tdee = int(tdee * 0.85)          # 15 % deficit
            protein_pct, carbs_pct, fat_pct = 0.35, 0.35, 0.30
        else:
            protein_pct, carbs_pct, fat_pct = 0.25, 0.50, 0.25

        return {
            "calories":  float(tdee),
            "protein_g": round(tdee * protein_pct / 4, 1),   # 4 kcal/g
            "carbs_g":   round(tdee * carbs_pct   / 4, 1),   # 4 kcal/g
            "fat_g":     round(tdee * fat_pct     / 9, 1),   # 9 kcal/g
        }

    # ------------------------------------------------------------------ #
    #  Serialisation                                                        #
    # ------------------------------------------------------------------ #
    def to_dict(self) -> Dict:
        return {
            "user_id":               self.user_id,
            "name":                  self.name,
            "age":                   self.age,
            "weight_kg":             self.weight_kg,
            "height_cm":             self.height_cm,
            "biological_sex":        self.biological_sex.value,
            "goals":                 [g.value for g in self.goals],
            "target_calories":       self.target_calories,
            "target_protein_g":      self.target_protein_g,
            "target_carbs_g":        self.target_carbs_g,
            "target_fat_g":          self.target_fat_g,
            "dietary_restrictions":  self.dietary_restrictions,
            "allergies":             self.allergies,
        }