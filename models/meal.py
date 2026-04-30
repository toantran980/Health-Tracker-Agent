"""Meal and Nutrition Data Models"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class MealType(Enum):
    """Meal classifications"""
    BREAKFAST = "breakfast"
    LUNCH     = "lunch"
    DINNER    = "dinner"
    SNACK     = "snack"


@dataclass
class NutritionInfo:
    """Nutritional information for a food item or aggregated meal."""
    calories:   float
    protein_g:  float
    carbs_g:    float
    fat_g:      float
    fiber_g:    float = 0.0
    sodium_mg:  float = 0.0
    sugar_g:    float = 0.0

    def get_macro_ratio(self) -> Dict[str, float]:
        """
        Return each macro as a percentage of total caloric contribution.

        Uses Atwater factors: protein 4 kcal/g, carbs 4 kcal/g, fat 9 kcal/g.
        Clamps denominator to 1 to avoid ZeroDivisionError on empty logs.
        """
        cal_from_macros = (
            self.protein_g * 4 +
            self.carbs_g   * 4 +
            self.fat_g     * 9
        )
        total = max(cal_from_macros, 1.0)
        return {
            "protein_percent": (self.protein_g * 4) / total * 100,
            "carbs_percent":   (self.carbs_g   * 4) / total * 100,
            "fat_percent":     (self.fat_g     * 9) / total * 100,
        }

    def __add__(self, other: "NutritionInfo") -> "NutritionInfo":
        """
        Support NutritionInfo + NutritionInfo so aggregation can use sum().

        Example:
            total = sum(items, start=NutritionInfo(0,0,0,0))
        """
        return NutritionInfo(
            calories=  self.calories  + other.calories,
            protein_g= self.protein_g + other.protein_g,
            carbs_g=   self.carbs_g   + other.carbs_g,
            fat_g=     self.fat_g     + other.fat_g,
            fiber_g=   self.fiber_g   + other.fiber_g,
            sodium_mg= self.sodium_mg + other.sodium_mg,
            sugar_g=   self.sugar_g   + other.sugar_g,
        )

    def __radd__(self, other: "NutritionInfo | int") -> "NutritionInfo":
        """Allow sum() with integer start value (0 + NutritionInfo)."""
        if isinstance(other, int):          # handles sum()'s implicit 0 start
            return self
        return self.__add__(other)


@dataclass
class FoodItem:
    """A single food item with nutritional metadata."""
    food_id:           str
    name:              str
    nutrition_info:    NutritionInfo
    serving_size:      str            = "100g"
    category:          str            = "other"
    tags:              List[str]      = field(default_factory=list)
    is_vegan:          bool           = False
    is_gluten_free:    bool           = False
    is_vegetarian:     bool           = False
    satisfaction_score: Optional[float] = None   # average user rating 1-10

    def to_dict(self) -> Dict:
        return {
            "food_id":   self.food_id,
            "name":      self.name,
            "calories":  self.nutrition_info.calories,
            "protein_g": self.nutrition_info.protein_g,
            "carbs_g":   self.nutrition_info.carbs_g,
            "fat_g":     self.nutrition_info.fat_g,
            "category":  self.category,
            "tags":      self.tags,
        }


@dataclass
class Meal:
    """A single logged meal composed of one or more food items."""
    meal_id:            str
    user_id:            str
    meal_type:          MealType
    timestamp:          datetime
    food_items:         List[FoodItem]   = field(default_factory=list)
    notes:              str              = ""
    satisfaction_score: Optional[int]   = None   # 1-10 user satisfaction

    def get_total_nutrition(self) -> NutritionInfo:
        """
        Aggregate nutrition across all food items in a single pass.

        Previously iterated food_items once per macro field (5×).
        Now uses __add__ / __radd__ on NutritionInfo so the list is
        traversed exactly once.
        """
        if not self.food_items:
            return NutritionInfo(0, 0, 0, 0)
        return sum(f.nutrition_info for f in self.food_items)   # type: ignore[return-value]

    def get_macro_balance(self) -> str:
        """Classify the meal's macro composition."""
        macros = self.get_total_nutrition().get_macro_ratio()
        protein_ok = 30 <= macros["protein_percent"] <= 40
        carbs_ok   = 45 <= macros["carbs_percent"]   <= 65
        fat_ok     = 20 <= macros["fat_percent"]     <= 35

        if protein_ok and carbs_ok and fat_ok:
            return "balanced"
        if macros["protein_percent"] > 40:
            return "high_protein"
        if macros["carbs_percent"] > 65:
            return "high_carb"
        return "unbalanced"


@dataclass
class DailyNutritionLog:
    """Aggregated nutrition record for a single calendar day."""
    log_id:  str
    user_id: str
    date:    datetime
    meals:   List[Meal] = field(default_factory=list)

    def get_total_nutrition(self) -> NutritionInfo:
        """
        Aggregate nutrition across all meals in a single pass.

        Previous implementation called m.get_total_nutrition() once per
        macro field (5 calls × N meals = 5N iterations).  Now each meal's
        nutrition is computed once, stored, and summed — O(N) total.
        """
        if not self.meals:
            return NutritionInfo(0, 0, 0, 0)
        return sum(m.get_total_nutrition() for m in self.meals)   # type: ignore[return-value]

    def get_adherence_ratio(self, target_nutrition: "NutritionInfo") -> float:
        """
        Multi-macro adherence score in [0, 1].

        Previous implementation checked calories only, silently ignoring
        protein, carbs, and fat — meaning the NutritionAnalyzer's
        statistical pipeline was built on an incomplete signal.

        Now each macro is scored as:

            score_k = 1 − |actual_k / target_k − 1|   (clamped to [0, 1])

        The four scores are averaged so all macros contribute equally.
        A perfect day on all four macros returns 1.0; missing every target
        by 100 % returns 0.0.
        """
        actual = self.get_total_nutrition()

        def score(actual_val: float, target_val: float) -> float:
            if target_val == 0:
                return 1.0
            ratio = actual_val / target_val
            return max(0.0, 1.0 - abs(1.0 - ratio))

        scores = [
            score(actual.calories,  target_nutrition.calories),
            score(actual.protein_g, target_nutrition.protein_g),
            score(actual.carbs_g,   target_nutrition.carbs_g),
            score(actual.fat_g,     target_nutrition.fat_g),
        ]
        return sum(scores) / len(scores)