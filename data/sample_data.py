"""Sample data and food database"""
from models.meal import FoodItem, NutritionInfo
from models.user_profile import UserProfile, Goal

# Sample food database
SAMPLE_FOODS = [
    FoodItem(
        food_id="chicken_breast",
        name="Grilled Chicken Breast",
        nutrition_info=NutritionInfo(
            calories=165, protein_g=31, carbs_g=0, fat_g=3.6
        ),
        category="protein",
        tags=["lean_protein", "high_protein"],
        is_vegan=False,
        is_vegetarian=False,
        is_gluten_free=True,
        satisfaction_score=8.5
    ),
    FoodItem(
        food_id="brown_rice",
        name="Brown Rice (1 cup cooked)",
        nutrition_info=NutritionInfo(
            calories=215, protein_g=5, carbs_g=45, fat_g=1.8
        ),
        category="carbs",
        tags=["whole_grain", "complex_carbs"],
        is_vegan=True,
        is_vegetarian=True,
        is_gluten_free=True,
        satisfaction_score=7.0
    ),
    FoodItem(
        food_id="broccoli",
        name="Broccoli (2 cups)",
        nutrition_info=NutritionInfo(
            calories=66, protein_g=4.3, carbs_g=12, fat_g=0.7, fiber_g=2.4
        ),
        category="vegetables",
        tags=["low_calorie", "high_fiber", "nutrient_dense"],
        is_vegan=True,
        is_vegetarian=True,
        is_gluten_free=True,
        satisfaction_score=6.5
    ),
    FoodItem(
        food_id="salmon",
        name="Salmon Fillet (100g)",
        nutrition_info=NutritionInfo(
            calories=206, protein_g=22, carbs_g=0, fat_g=13, fiber_g=0
        ),
        category="protein",
        tags=["omega3", "fatty_fish", "high_protein"],
        is_vegan=False,
        is_vegetarian=False,
        is_gluten_free=True,
        satisfaction_score=9.0
    ),
    FoodItem(
        food_id="eggs",
        name="Scrambled Eggs (2 large)",
        nutrition_info=NutritionInfo(
                calories=155, protein_g=13, carbs_g=1.1, fat_g=11
            ),
                category="protein",
                tags=["eggs", "high_protein", "breakfast"],
                is_vegan=False,
                is_vegetarian=True,
                is_gluten_free=True,
                satisfaction_score=8.0
            ),
            FoodItem(
                food_id="Greek yogurt",
                name="Greek Yogurt (200g)",
                nutrition_info=NutritionInfo(
                    calories=130, protein_g=23, carbs_g=9, fat_g=0.4
                ),
                category="dairy",
                tags=["high_protein", "probiotics"],
                is_vegan=False,
                is_vegetarian=True,
                is_gluten_free=True,
                satisfaction_score=8.0
            ),
            FoodItem(
                food_id="almonds",
                name="Almonds (1 oz / 23 nuts)",
                nutrition_info=NutritionInfo(
                    calories=164, protein_g=6, carbs_g=6, fat_g=14, fiber_g=3.5
                ),
                category="nuts",
                tags=["healthy_fats", "snack", "nutrient_dense"],
                is_vegan=True,
                is_vegetarian=True,
                is_gluten_free=True,
                satisfaction_score=8.5
            ),
            FoodItem(
                food_id="sweet_potato",
                name="Sweet Potato (medium, baked)",
                nutrition_info=NutritionInfo(
                    calories=103, protein_g=2.3, carbs_g=24, fat_g=0.1, fiber_g=3.9
                ),
                category="carbs",
                tags=["complex_carbs", "vegan"],
                is_vegan=True,
                is_vegetarian=True,
                is_gluten_free=True,
                satisfaction_score=7.5
            ),
            FoodItem(
                food_id="avocado",
                name="Avocado (0.5 fruit)",
                nutrition_info=NutritionInfo(
                    calories=120, protein_g=1.5, carbs_g=6, fat_g=11, fiber_g=5
                ),
                category="fats",
                tags=["healthy_fats", "vegan"],
                is_vegan=True,
                is_vegetarian=True,
                is_gluten_free=True,
                satisfaction_score=8.5
            ),
            FoodItem(
                food_id="spinach",
                name="Spinach Salad (3 cups raw)",
                nutrition_info=NutritionInfo(
                    calories=20, protein_g=2.7, carbs_g=3.6, fat_g=0.4, fiber_g=2.2
                ),
                category="vegetables",
                tags=["leafy_green", "low_calorie"],
                is_vegan=True,
                is_vegetarian=True,
                is_gluten_free=True,
                satisfaction_score=6.0
            ),
            FoodItem(
                food_id="oatmeal",
                name="Oatmeal (1 cup cooked)",
                nutrition_info=NutritionInfo(
                    calories=150, protein_g=5, carbs_g=27, fat_g=3, fiber_g=4
                ),
                category="carbs",
                tags=["breakfast", "fiber"],
                is_vegan=True,
                is_vegetarian=True,
                is_gluten_free=False,
                satisfaction_score=7.0
            ),
        ]


def create_sample_user() -> UserProfile:
    """Create sample user for testing"""
    return UserProfile(
        user_id="sample_user_001",
        name="John Doe",
        age=22,
        weight_kg=75,
        height_cm=180,
        goals=[Goal.ENERGY_OPTIMIZATION, Goal.GENERAL_WELLNESS],
        dietary_restrictions=[],
        allergies=[],
        preferred_cuisine=["Asian", "Mediterranean"],
        target_calories=2200,
        target_protein_g=150,
        target_carbs_g=250,
        target_fat_g=65,
        work_hours_per_day=8,
        study_hours_per_day=3,
        current_sleep_hours=7.5,
        current_energy_level=6
    )
