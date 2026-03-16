"""User Profile Data Model"""
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime
from enum import Enum


class Goal(Enum):
    """User health goals"""
    WEIGHT_LOSS = "weight_loss"
    MUSCLE_GAIN = "muscle_gain"
    ENERGY_OPTIMIZATION = "energy_optimization"
    GENERAL_WELLNESS = "general_wellness"


@dataclass
class UserProfile:
    """Comprehensive user profile for health tracking"""
    user_id: str
    name: str
    age: int
    weight_kg: float
    height_cm: float
    goals: List[Goal] = field(default_factory=lambda: [Goal.GENERAL_WELLNESS])
    
    # Dietary preferences
    dietary_restrictions: List[str] = field(default_factory=list)  # "vegan", "gluten_free", etc.
    allergies: List[str] = field(default_factory=list)
    preferred_cuisine: List[str] = field(default_factory=list)
    
    # Nutritional targets (daily)
    target_calories: int = 2000
    target_protein_g: float = 50.0
    target_carbs_g: float = 250.0
    target_fat_g: float = 65.0
    
    # Study/Work preferences
    work_hours_per_day: int = 8
    study_hours_per_day: int = 2
    max_study_session_duration: int = 120  # minutes
    min_study_session_duration: int = 25   # minutes
    
    # Availability windows (hours in 24-hour format)
    earliest_study_time: int = 8
    latest_study_time: int = 22
    
    # Current metrics
    current_sleep_hours: float = 8.0
    current_energy_level: int = 5  # 1-10 scale
    current_weight_kg: float = field(default=0)
    
    # Behavioral data
    daily_logs: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.current_weight_kg == 0:
            self.current_weight_kg = self.weight_kg
    
    def get_bmr(self) -> float:
        """Calculate Basal Metabolic Rate using Mifflin-St Jeor equation"""
        if self.age < 18:
            return self.weight_kg * 20
        # Simplified calculation (typical for adults)
        return 10 * self.weight_kg + 6.25 * self.height_cm - 5 * self.age + 5
    
    def get_tdee(self, activity_level: float = 1.5) -> int:
        """Calculate Total Daily Energy Expenditure"""
        return int(self.get_bmr() * activity_level)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "user_id": self.user_id,
            "name": self.name,
            "age": self.age,
            "weight_kg": self.weight_kg,
            "height_cm": self.height_cm,
            "goals": [g.value for g in self.goals],
            "target_calories": self.target_calories,
            "target_protein_g": self.target_protein_g,
            "dietary_restrictions": self.dietary_restrictions,
            "allergies": self.allergies,
        }
