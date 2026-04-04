import kagglehub
import os
import pandas as pd
from typing import List
from models.meal import FoodItem, NutritionInfo

def load_kaggle_food_dataset(limit: int = 1500) -> List[FoodItem]:
    """
    Downloads and parses the Kaggle Food Nutrition Dataset using kagglehub.
    Maps columns to the application's FoodItem and NutritionInfo models.
    """
    try:
        # Download the dataset (will use cached version if already downloaded)
        dataset_path = kagglehub.dataset_download("utsavdey1410/food-nutrition-dataset")
        
        # Find the CSV file inside the downloaded directory
        csv_file = None
        for root, dirs, files in os.walk(dataset_path):
            for file in files:
                if file.endswith('.csv'):
                    csv_file = os.path.join(root, file)
                    break
            if csv_file:
                break
                
        if not csv_file:
            print("Warning: Could not find CSV file in Kaggle dataset. Returning empty dataset.")
            return []
            
        print(f"Loading dataset from {csv_file}...")
        df = pd.read_csv(csv_file)
        
        # Limit rows for fast API startup and cosine similarity performance
        if limit is not None and limit > 0:
            df = df.head(limit)
            
        # Ensure target columns exist
        col_map = {
            'Calories': 'Caloric Value',
            'Protein': 'Protein',
            'Carbs': 'Carbohydrates',
            'Fat': 'Fat',
            'Fiber': 'Dietary Fiber',
            'Sodium': 'Sodium',
            'Sugar': 'Sugars'
        }
        
        # Convert necessary columns to numeric, filling NaNs with 0
        for col_internal, col_csv in col_map.items():
            if col_csv in df.columns:
                df[col_csv] = pd.to_numeric(df[col_csv], errors='coerce').fillna(0.0)
            
        food_items = []
        for index, row in df.iterrows():
            # Build NutritionInfo object
            nutrition = NutritionInfo(
                calories=float(row.get('Caloric Value', 0.0)),
                protein_g=float(row.get('Protein', 0.0)),
                carbs_g=float(row.get('Carbohydrates', 0.0)),
                fat_g=float(row.get('Fat', 0.0)),
                fiber_g=float(row.get('Dietary Fiber', 0.0)),
                sodium_mg=float(row.get('Sodium', 0.0)),
                sugar_g=float(row.get('Sugars', 0.0))
            )
            
            # Construct FoodItem with required attributes
            food_name = str(row.get('food', f'Unknown Food {index}'))
            food = FoodItem(
                food_id=f"kaggle_food_{index}",
                name=food_name.strip(),
                nutrition_info=nutrition,
                category="Kaggle Dataset"  # Generic category
            )
            food_items.append(food)
            
        print(f"Successfully loaded {len(food_items)} food items from first Kaggle dataset.")

        # --- SECOND DATASET ---
        try:
            dataset_path_2 = kagglehub.dataset_download("niharika41298/nutrition-details-for-most-common-foods")
            csv_file_2 = None
            for root, dirs, files in os.walk(dataset_path_2):
                for file in files:
                    if file.endswith('.csv'):
                        csv_file_2 = os.path.join(root, file)
                        break
                if csv_file_2:
                    break
            
            if csv_file_2:
                print(f"Loading second dataset from {csv_file_2}...")
                df_2 = pd.read_csv(csv_file_2)
                if limit is not None and limit > 0:
                    df_2 = df_2.head(limit)
                    
                col_map_2 = ['Calories', 'Protein', 'Carbs', 'Fat', 'Fiber']
                for col in col_map_2:
                    if col in df_2.columns:
                        # Some datasets use text like 't' for trace amounts; we'll remove text and coerce everything else to 0
                        df_2[col] = pd.to_numeric(df_2[col].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0.0)
                
                for index, row in df_2.iterrows():
                    nutrition = NutritionInfo(
                        calories=float(row.get('Calories', 0.0)),
                        protein_g=float(row.get('Protein', 0.0)),
                        carbs_g=float(row.get('Carbs', 0.0)),
                        fat_g=float(row.get('Fat', 0.0)),
                        fiber_g=float(row.get('Fiber', 0.0)),
                    )
                    food_name = str(row.get('Food', f'Kaggle Common Food {index}'))
                    food = FoodItem(
                        food_id=f"kaggle_common_{index}",
                        name=food_name.strip(),
                        nutrition_info=nutrition,
                        category=str(row.get('Category', 'Common Foods'))
                    )
                    food_items.append(food)
                print(f"Successfully merged second Kaggle dataset. Total items: {len(food_items)}")
        except Exception as e:
            print(f"Error loading second Kaggle dataset: {e}")

        return food_items
        
    except Exception as e:
        print(f"Error loading Kaggle dataset: {e}")
        return []

if __name__ == "__main__":
    items = load_kaggle_food_dataset(limit=5)
    for item in items:
        print(item.name, item.nutrition_info)
