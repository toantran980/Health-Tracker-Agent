"""Meal and Nutrition Data Models"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class MealType(Enum):
    """Meal classifications"""
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACK = "snack"


@dataclass
class NutritionInfo:
    """Nutritional information for food items"""
    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float
    fiber_g: float = 0.0
    sodium_mg: float = 0.0
    sugar_g: float = 0.0
    
    def get_macro_ratio(self) -> Dict[str, float]:
        """Get macro ratio as percentage"""
        total_calories = max(self.protein_g * 4 + self.carbs_g * 4 + self.fat_g * 9, 1)
        return {
            "protein_percent": (self.protein_g * 4) / total_calories * 100,
            "carbs_percent": (self.carbs_g * 4) / total_calories * 100,
            "fat_percent": (self.fat_g * 9) / total_calories * 100,
        }


@dataclass
class FoodItem:
    """Food item record"""
    food_id: str
    name: str
    nutrition_info: NutritionInfo
    serving_size: str = "100g"
    category: str = "other"
    tags: List[str] = field(default_factory=list)
    is_vegan: bool = False
    is_gluten_free: bool = False
    is_vegetarian: bool = False
    satisfaction_score: Optional[float] = None  # User average rating 1-10
    
    def to_dict(self) -> Dict:
        return {
            "food_id": self.food_id,
            "name": self.name,
            "calories": self.nutrition_info.calories,
            "protein_g": self.nutrition_info.protein_g,
            "carbs_g": self.nutrition_info.carbs_g,
            "fat_g": self.nutrition_info.fat_g,
            "category": self.category,
            "tags": self.tags,
        }


@dataclass
class Meal:
    """Logged meal record"""
    meal_id: str
    user_id: str
    meal_type: MealType
    timestamp: datetime
    food_items: List[FoodItem] = field(default_factory=list)
    notes: str = ""
    satisfaction_score: Optional[int] = None  # 1-10 user satisfaction
    
    def get_total_nutrition(self) -> NutritionInfo:
        """Calculate total nutrition for the meal"""
        total_calories = sum(f.nutrition_info.calories for f in self.food_items)
        total_protein = sum(f.nutrition_info.protein_g for f in self.food_items)
        total_carbs = sum(f.nutrition_info.carbs_g for f in self.food_items)
        total_fat = sum(f.nutrition_info.fat_g for f in self.food_items)
        total_fiber = sum(f.nutrition_info.fiber_g for f in self.food_items)
        
        return NutritionInfo(
            calories=total_calories,
            protein_g=total_protein,
            carbs_g=total_carbs,
            fat_g=total_fat,
            fiber_g=total_fiber,
        )
    
    def get_macro_balance(self) -> str:
        """Assess macro balance quality"""
        macros = self.get_total_nutrition().get_macro_ratio()
        protein_good = 30 <= macros["protein_percent"] <= 40
        carbs_good = 45 <= macros["carbs_percent"] <= 65
        fat_good = 20 <= macros["fat_percent"] <= 35
        
        if protein_good and carbs_good and fat_good:
            return "balanced"
        elif macros["protein_percent"] > 40:
            return "high_protein"
        elif macros["carbs_percent"] > 65:
            return "high_carb"
        else:
            return "unbalanced"


@dataclass
class DailyNutritionLog:
    """Daily nutrition summary"""
    log_id: str
    user_id: str
    date: datetime
    meals: List[Meal] = field(default_factory=list)
    
    def get_total_nutrition(self) -> NutritionInfo:
        """Sum nutrition for all meals"""
        total_calories = sum(m.get_total_nutrition().calories for m in self.meals)
        total_protein = sum(m.get_total_nutrition().protein_g for m in self.meals)
        total_carbs = sum(m.get_total_nutrition().carbs_g for m in self.meals)
        total_fat = sum(m.get_total_nutrition().fat_g for m in self.meals)
        total_fiber = sum(m.get_total_nutrition().fiber_g for m in self.meals)
        
        return NutritionInfo(
            calories=total_calories,
            protein_g=total_protein,
            carbs_g=total_carbs,
            fat_g=total_fat,
            fiber_g=total_fiber,
        )
    
    def get_adherence_ratio(self, target_nutrition: NutritionInfo) -> float:
        """Calculate adherence to target nutrition (within ±10%)"""
        actual = self.get_total_nutrition()
        lower_bound = target_nutrition.calories * 0.9
        upper_bound = target_nutrition.calories * 1.1
        
        if lower_bound <= actual.calories <= upper_bound:
            return 1.0
        elif actual.calories < lower_bound:
            return actual.calories / target_nutrition.calories
        else:
            return target_nutrition.calories / actual.calories
