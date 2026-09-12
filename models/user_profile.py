"""User Profile Data Model"""
from dataclasses import dataclass, field
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

    # Identity
    user_id:    str
    name:       str
    age:        int
    weight_kg:  float
    height_cm:  float
    biological_sex: BiologicalSex = BiologicalSex.MALE   # affects BMR formula

    # Auth (optional; enabled by setting a password on create/login)
    password_hash: str = ""   # werkzeug PBKDF2 hash; empty = password not set

    # Health goals
    goals: list[Goal] = field(default_factory=lambda: [Goal.GENERAL_WELLNESS])

    # Dietary preferences
    dietary_restrictions: list[str] = field(default_factory=list)  # "vegan", "gluten_free", …
    allergies:            list[str] = field(default_factory=list)
    preferred_cuisine:    list[str] = field(default_factory=list)

    # Daily nutrition targets
    target_calories:  int   = 2000
    target_protein_g: float = 50.0
    target_carbs_g:   float = 250.0
    target_fat_g:     float = 65.0

    # Hydration target (mL/day) — default per common guidance; user-configurable
    water_target_ml: int = 2500

    # Milestone targets
    target_weight_kg: float = 0.0                # 0.0 means unassigned / infer from goal
    weekly_exercise_target_minutes: int = 150    # default per WHO benchmark

    # Study and work schedule
    work_hours_per_day:           int = 8
    study_hours_per_day:          int = 2
    max_study_session_duration:   int = 120   # minutes
    min_study_session_duration:   int = 25    # minutes
    earliest_study_time:          int = 8     # 24-hour clock
    latest_study_time:            int = 22    # 24-hour clock

    # Current metrics
    current_sleep_hours:  float = 8.0
    current_energy_level: int   = 5    # 1-10 scale
    current_weight_kg:    float = 0.0  # initialised in __post_init__

    # Behavioral history
    daily_logs: list[dict] = field(default_factory=list)
    created_at: datetime   = field(default_factory=datetime.now)

    # Post-init
    def __post_init__(self) -> None:
        if self.current_weight_kg == 0.0:
            self.current_weight_kg = self.weight_kg

    # Physiological calculations
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

    def to_dict(self) -> dict:
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
            "water_target_ml":               self.water_target_ml,
            "target_weight_kg":              self.target_weight_kg,
            "weekly_exercise_target_minutes": self.weekly_exercise_target_minutes,
            "dietary_restrictions":          self.dietary_restrictions,
            "allergies":                     self.allergies,
            "password_set":                  bool(self.password_hash),
        }

    def to_public_dict(self) -> dict:
        """Same as to_dict, guaranteed to never expose the password hash."""
        payload = self.to_dict()
        payload.pop("password_hash", None)
        return payload