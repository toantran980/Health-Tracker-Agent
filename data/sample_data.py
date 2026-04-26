"""Sample data and food database"""
from models.meal import FoodItem, NutritionInfo
from models.user_profile import UserProfile, Goal, BiologicalSex


# Food database: 25 items with varied nutrition profiles
SAMPLE_FOODS = [

    # High protein, low carb
    FoodItem(
        food_id="chicken_breast",
        name="Grilled Chicken Breast (150g)",
        nutrition_info=NutritionInfo(calories=165, protein_g=31, carbs_g=0,  fat_g=3.6),
        category="protein",
        tags=["lean_protein", "high_protein"],
        is_vegan=False, is_vegetarian=False, is_gluten_free=True,
        satisfaction_score=8.5,
    ),
    FoodItem(
        food_id="salmon",
        name="Salmon Fillet (100g)",
        nutrition_info=NutritionInfo(calories=206, protein_g=22, carbs_g=0,  fat_g=13),
        category="protein",
        tags=["omega3", "fatty_fish", "high_protein"],
        is_vegan=False, is_vegetarian=False, is_gluten_free=True,
        satisfaction_score=9.0,
    ),
    FoodItem(
        food_id="tuna_can",
        name="Canned Tuna in Water (150g)",
        nutrition_info=NutritionInfo(calories=150, protein_g=33, carbs_g=0,  fat_g=1.5),
        category="protein",
        tags=["lean_protein", "high_protein"],
        is_vegan=False, is_vegetarian=False, is_gluten_free=True,
        satisfaction_score=7.0,
    ),
    FoodItem(
        food_id="eggs",
        name="Scrambled Eggs (2 large)",
        nutrition_info=NutritionInfo(calories=155, protein_g=13, carbs_g=1.1, fat_g=11),
        category="protein",
        tags=["eggs", "high_protein", "breakfast"],
        is_vegan=False, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=8.0,
    ),
    FoodItem(
        food_id="greek_yogurt",          # fixed: was "Greek yogurt"
        name="Greek Yogurt (200g)",
        nutrition_info=NutritionInfo(calories=130, protein_g=23, carbs_g=9,  fat_g=0.4),
        category="dairy",
        tags=["high_protein", "probiotics"],
        is_vegan=False, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=8.0,
    ),
    FoodItem(
        food_id="cottage_cheese",
        name="Cottage Cheese (200g)",
        nutrition_info=NutritionInfo(calories=180, protein_g=25, carbs_g=6,  fat_g=5),
        category="dairy",
        tags=["high_protein", "low_fat"],
        is_vegan=False, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.0,
    ),
    FoodItem(
        food_id="turkey_breast",
        name="Turkey Breast (150g)",
        nutrition_info=NutritionInfo(calories=160, protein_g=30, carbs_g=0,  fat_g=3.5),
        category="protein",
        tags=["lean_protein", "high_protein"],
        is_vegan=False, is_vegetarian=False, is_gluten_free=True,
        satisfaction_score=7.5,
    ),

    # Complex carbs
    FoodItem(
        food_id="brown_rice",
        name="Brown Rice (1 cup cooked)",
        nutrition_info=NutritionInfo(calories=215, protein_g=5,  carbs_g=45, fat_g=1.8),
        category="carbs",
        tags=["whole_grain", "complex_carbs"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.0,
    ),
    FoodItem(
        food_id="oatmeal",
        name="Oatmeal (1 cup cooked)",
        nutrition_info=NutritionInfo(calories=150, protein_g=5,  carbs_g=27, fat_g=3,  fiber_g=4),
        category="carbs",
        tags=["breakfast", "fiber"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=False,
        satisfaction_score=7.0,
    ),
    FoodItem(
        food_id="sweet_potato",
        name="Sweet Potato (medium, baked)",
        nutrition_info=NutritionInfo(calories=103, protein_g=2.3, carbs_g=24, fat_g=0.1, fiber_g=3.9),
        category="carbs",
        tags=["complex_carbs", "vegan"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.5,
    ),
    FoodItem(
        food_id="quinoa",
        name="Quinoa (1 cup cooked)",
        nutrition_info=NutritionInfo(calories=222, protein_g=8,  carbs_g=39, fat_g=3.5, fiber_g=5),
        category="carbs",
        tags=["complete_protein", "whole_grain", "vegan"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.5,
    ),
    FoodItem(
        food_id="whole_wheat_bread",
        name="Whole Wheat Bread (2 slices)",
        nutrition_info=NutritionInfo(calories=160, protein_g=8,  carbs_g=30, fat_g=2,  fiber_g=4),
        category="carbs",
        tags=["whole_grain", "breakfast"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=False,
        satisfaction_score=6.5,
    ),
    FoodItem(
        food_id="banana",
        name="Banana (1 medium)",
        nutrition_info=NutritionInfo(calories=105, protein_g=1.3, carbs_g=27, fat_g=0.4, fiber_g=3.1),
        category="fruit",
        tags=["quick_energy", "potassium", "vegan"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=8.0,
    ),

    # Healthy fats
    FoodItem(
        food_id="avocado",
        name="Avocado (0.5 fruit)",
        nutrition_info=NutritionInfo(calories=120, protein_g=1.5, carbs_g=6,  fat_g=11, fiber_g=5),
        category="fats",
        tags=["healthy_fats", "vegan"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=8.5,
    ),
    FoodItem(
        food_id="almonds",
        name="Almonds (1 oz / 23 nuts)",
        nutrition_info=NutritionInfo(calories=164, protein_g=6,  carbs_g=6,  fat_g=14, fiber_g=3.5),
        category="nuts",
        tags=["healthy_fats", "snack", "nutrient_dense"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=8.5,
    ),
    FoodItem(
        food_id="peanut_butter",
        name="Peanut Butter (2 tbsp)",
        nutrition_info=NutritionInfo(calories=190, protein_g=8,  carbs_g=6,  fat_g=16),
        category="fats",
        tags=["healthy_fats", "snack"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=9.0,
    ),
    FoodItem(
        food_id="olive_oil",
        name="Olive Oil (1 tbsp)",
        nutrition_info=NutritionInfo(calories=119, protein_g=0,  carbs_g=0,  fat_g=13.5),
        category="fats",
        tags=["healthy_fats", "cooking"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.0,
    ),

    # Vegetables
    FoodItem(
        food_id="broccoli",
        name="Broccoli (2 cups steamed)",
        nutrition_info=NutritionInfo(calories=66, protein_g=4.3, carbs_g=12, fat_g=0.7, fiber_g=2.4),
        category="vegetables",
        tags=["low_calorie", "high_fiber", "nutrient_dense"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=6.5,
    ),
    FoodItem(
        food_id="spinach",
        name="Spinach Salad (3 cups raw)",
        nutrition_info=NutritionInfo(calories=20, protein_g=2.7, carbs_g=3.6, fat_g=0.4, fiber_g=2.2),
        category="vegetables",
        tags=["leafy_green", "low_calorie"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=6.0,
    ),
    FoodItem(
        food_id="mixed_vegetables",
        name="Mixed Stir-Fry Vegetables (2 cups)",
        nutrition_info=NutritionInfo(calories=80, protein_g=4,  carbs_g=14, fat_g=0.5, fiber_g=4),
        category="vegetables",
        tags=["low_calorie", "high_fiber", "vegan"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.0,
    ),

    # Legumes and plant protein
    FoodItem(
        food_id="black_beans",
        name="Black Beans (1 cup cooked)",
        nutrition_info=NutritionInfo(calories=227, protein_g=15, carbs_g=41, fat_g=0.9, fiber_g=15),
        category="legumes",
        tags=["plant_protein", "high_fiber", "vegan"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.5,
    ),
    FoodItem(
        food_id="lentils",
        name="Red Lentils (1 cup cooked)",
        nutrition_info=NutritionInfo(calories=230, protein_g=18, carbs_g=40, fat_g=0.8, fiber_g=16),
        category="legumes",
        tags=["plant_protein", "high_fiber", "vegan"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.0,
    ),
    FoodItem(
        food_id="tofu",
        name="Firm Tofu (150g)",
        nutrition_info=NutritionInfo(calories=120, protein_g=13, carbs_g=3,  fat_g=6),
        category="protein",
        tags=["plant_protein", "vegan", "high_protein"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=6.5,
    ),

    # High-calorie options for contrast
    FoodItem(
        food_id="protein_shake",
        name="Whey Protein Shake (1 scoop + water)",
        nutrition_info=NutritionInfo(calories=120, protein_g=25, carbs_g=3,  fat_g=1.5),
        category="supplement",
        tags=["high_protein", "post_workout"],
        is_vegan=False, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.0,
    ),
    FoodItem(
        food_id="white_rice",
        name="White Rice (1 cup cooked)",
        nutrition_info=NutritionInfo(calories=242, protein_g=4.4, carbs_g=53, fat_g=0.4),
        category="carbs",
        tags=["simple_carbs", "high_gi"],
        is_vegan=True, is_vegetarian=True, is_gluten_free=True,
        satisfaction_score=7.0,
    ),
]


# Sample users with contrasting goals

def create_sample_user() -> UserProfile:
    """
    Primary demo user: male, 22, energy optimisation goal.
    Targets set above TDEE to support active student lifestyle.
    """
    return UserProfile(
        user_id="user_001",
        name="John Doe",
        age=22,
        weight_kg=75,
        height_cm=180,
        biological_sex=BiologicalSex.MALE,
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
        current_energy_level=6,
    )


def create_sample_user_muscle() -> UserProfile:
    """
    Secondary demo user: male, 24, muscle gain goal.
    High protein target demonstrates different recommendation output.
    """
    return UserProfile(
        user_id="user_002",
        name="Alex Kim",
        age=24,
        weight_kg=80,
        height_cm=178,
        biological_sex=BiologicalSex.MALE,
        goals=[Goal.MUSCLE_GAIN],
        dietary_restrictions=[],
        allergies=[],
        preferred_cuisine=["American", "Japanese"],
        target_calories=2800,
        target_protein_g=200,
        target_carbs_g=300,
        target_fat_g=70,
        work_hours_per_day=6,
        study_hours_per_day=2,
        current_sleep_hours=8.0,
        current_energy_level=8,
    )


def create_sample_user_weightloss() -> UserProfile:
    """
    Tertiary demo user: female, 21, weight loss goal.
    Lower calorie target and vegan restriction tests constraint filtering.
    """
    return UserProfile(
        user_id="user_003",
        name="Sara Patel",
        age=21,
        weight_kg=62,
        height_cm=165,
        biological_sex=BiologicalSex.FEMALE,
        goals=[Goal.WEIGHT_LOSS],
        dietary_restrictions=["vegan"],
        allergies=["tree_nuts"],          # filters out almonds
        preferred_cuisine=["Indian", "Mediterranean"],
        target_calories=1600,
        target_protein_g=100,
        target_carbs_g=180,
        target_fat_g=45,
        work_hours_per_day=7,
        study_hours_per_day=4,
        current_sleep_hours=7.0,
        current_energy_level=5,
    )