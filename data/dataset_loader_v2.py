"""Load and merge food data from sample entries and nutrition CSV files."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import uuid
import pandas as pd
from models.meal import FoodItem, NutritionInfo

logger = logging.getLogger(__name__)

# All CSV files
GROUP_FILES = [
    "data/nutrition_data/FOOD-DATA-GROUP1.csv",
    "data/nutrition_data/FOOD-DATA-GROUP2.csv",
    "data/nutrition_data/FOOD-DATA-GROUP3.csv",
    "data/nutrition_data/FOOD-DATA-GROUP4.csv",
    "data/nutrition_data/FOOD-DATA-GROUP5.csv",
]

NUTRIENTS_FILE = "data/nutrition_data/nutrients_csvfile.csv"


# Column maps 
# GROUP files column → NutritionInfo field
GROUP_COL_MAP = {
    "calories":  "Caloric Value",
    "protein_g": "Protein",
    "carbs_g":   "Carbohydrates",
    "fat_g":     "Fat",
    "fiber_g":   "Dietary Fiber",
}

# nutrients_csvfile.csv column → NutritionInfo field
NUTRIENTS_COL_MAP = {
    "calories":  "Calories",
    "protein_g": "Protein",
    "carbs_g":   "Carbs",
    "fat_g":     "Fat",
    "fiber_g":   "Fiber",
}


def safe_float(value, default: float = 0.0) -> float:
    """Convert value to float safely, returning default on failure."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def load_group_files() -> list[FoodItem]:
    """Load all 5 GROUP CSV files (identical columns)."""
    all_dfs = []

    for path in GROUP_FILES:
        try:
            df = pd.read_csv(path)
            df = df.drop(columns=["Unnamed: 0.1", "Unnamed: 0"], errors="ignore")
            all_dfs.append(df)
            logger.info("  [Loader] %s — %d rows", path.split('/')[-1], len(df))
        except FileNotFoundError:
            logger.warning("  [Loader] Not found: %s", path)
        except Exception as e:
            logger.warning("  [Loader] Error reading %s: %s", path, e)

    if not all_dfs:
        return []

    # Combine all 5 into one dataframe
    combined = pd.concat(all_dfs, ignore_index=True)

    # Clean
    combined = combined.dropna(subset=["food", "Caloric Value"])
    combined = combined[pd.to_numeric(combined["Caloric Value"], errors="coerce") > 0]
    combined = combined.drop_duplicates(subset=["food"])

    foods = []
    for _, row in combined.iterrows():
        try:
            foods.append(FoodItem(
                food_id        = f"grp_{uuid.uuid4().hex[:8]}",
                name           = str(row["food"]).strip().title(),
                nutrition_info = NutritionInfo(
                    calories=  safe_float(row.get("Caloric Value")),
                    protein_g= safe_float(row.get("Protein")),
                    carbs_g=   safe_float(row.get("Carbohydrates")),
                    fat_g=     safe_float(row.get("Fat")),
                    fiber_g=   safe_float(row.get("Dietary Fiber")),
                ),
                category = "general",
                tags     = ["csv_imported", "group_data"],
            ))
        except Exception:
            continue

    return foods


def load_nutrients_file() -> list[FoodItem]:
    """Load nutrients_csvfile.csv (different column names, has Category)."""
    try:
        df = pd.read_csv(NUTRIENTS_FILE)

        # Replace trace amounts
        df = df.replace("t", 0)

        # Clean
        df["Calories"] = pd.to_numeric(df["Calories"], errors="coerce")
        df = df.dropna(subset=["Food", "Calories"])
        df = df[df["Calories"] > 0]
        df = df.drop_duplicates(subset=["Food"])

        logger.info("  [Loader] nutrients_csvfile.csv — %d rows", len(df))

        foods = []
        for _, row in df.iterrows():
            try:
                category = str(row.get("Category", "general")).strip()
                foods.append(FoodItem(
                    food_id        = f"nut_{uuid.uuid4().hex[:8]}",
                    name           = str(row["Food"]).strip().title(),
                    nutrition_info = NutritionInfo(
                        calories=  safe_float(row.get("Calories")),
                        protein_g= safe_float(row.get("Protein")),
                        carbs_g=   safe_float(row.get("Carbs")),
                        fat_g=     safe_float(row.get("Fat")),
                        fiber_g=   safe_float(row.get("Fiber")),
                    ),
                    category = category,
                    tags     = ["csv_imported", category.lower().replace(" ", "_")],
                ))
            except Exception:
                continue

        return foods

    except FileNotFoundError:
        logger.warning("  [Loader] Not found: %s", NUTRIENTS_FILE)
        return []
    except Exception as e:
        logger.warning("  [Loader] Error reading nutrients file: %s", e)
        return []


def load_food_database() -> list[FoodItem]:
    """
    Load full food database from all sources.

    Order:
        Existing sample_data (your handcrafted foods)
        GROUP1-5 CSV files  (2,395 foods, detailed micronutrients)
        nutrients_csvfile   (335 foods, has food categories)

    Deduplication is name-based so the same food from multiple
    sources doesn't appear twice.
    """
    foods      = []
    seen_names = set()

    # Layer 1: sample_data
    try:
        from data.sample_data import SAMPLE_FOODS
        for food in SAMPLE_FOODS:
            key = food.name.lower().strip()
            if key not in seen_names:
                foods.append(food)
                seen_names.add(key)
        logger.info("[Loader] sample_data — %d foods", len(SAMPLE_FOODS))
    except (ImportError, AttributeError):
        logger.warning("[Loader] No sample_data found, skipping")

    # Layer 2: GROUP CSV files 
    logger.info("[Loader] Loading GROUP files...")
    group_foods = load_group_files()
    added = 0
    for food in group_foods:
        key = food.name.lower().strip()
        if key not in seen_names:
            foods.append(food)
            seen_names.add(key)
            added += 1
    logger.info("[Loader] GROUP files total — %d unique foods added", added)

    # Layer 3: nutrients_csvfile
    logger.info("[Loader] Loading nutrients file...")
    nutrient_foods = load_nutrients_file()
    added = 0
    for food in nutrient_foods:
        key = food.name.lower().strip()
        if key not in seen_names:
            foods.append(food)
            seen_names.add(key)
            added += 1
    logger.info("[Loader] nutrients_csvfile — %d unique foods added", added)

    logger.info("[Loader] Total food database: %d items", len(foods))
    return foods


if __name__ == "__main__":
    db = load_food_database()
    print(f"\nSample foods:")
    for food in db[:5]:
        print(f"  {food.name:30s} | "
              f"{food.nutrition_info.calories:6.1f} kcal | "
              f"P:{food.nutrition_info.protein_g:5.1f}g | "
              f"C:{food.nutrition_info.carbs_g:5.1f}g | "
              f"F:{food.nutrition_info.fat_g:5.1f}g")