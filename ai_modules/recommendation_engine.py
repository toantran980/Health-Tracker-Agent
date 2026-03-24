"""Recommendation Engine - Personalized suggestions based on AI analysis"""
from typing import List, Dict, Optional
from datetime import datetime
from models.user_profile import UserProfile, Goal
from models.meal import FoodItem, NutritionInfo


class MealRecommendationEngine:
    """Content and collaborative filtering for meal recommendations"""
    
    def __init__(self, user_profile: UserProfile, food_database: List[FoodItem]):
        self.user_profile = user_profile
        self.food_database = food_database
        self.user_meal_history: List[Dict] = []
        self.user_ratings: Dict[str, float] = {}  # food_id -> rating (1-10)
    
    def rate_meal(self, food_id: str, rating: float):
        """Record user rating for a food"""
        self.user_ratings[food_id] = rating
    
    def add_meal_to_history(self, food_id: str, meal_type: str):
        """Add meal to user history"""
        self.user_meal_history.append({
            "food_id": food_id,
            "meal_type": meal_type,
            "timestamp": datetime.now()
        })
    
    def get_content_based_recommendations(self, n: int = 5) -> List[Dict]:
        """
        Content-based filtering: recommend meals similar to highly-rated meals
        """
        if not self.user_ratings:
            return self._get_default_recommendations(n)
        
        # Get highly-rated meals
        highly_rated = {fid: rating for fid, rating in self.user_ratings.items() if rating >= 7}
        
        if not highly_rated:
            return self._get_default_recommendations(n)
        
        recommendations = []
        scored_foods = {}
        
        for food in self.food_database:
            if food.food_id in highly_rated:
                continue  # Skip already-rated items
            
            # Calculate similarity to highly-rated meals
            similarity_score = 0.0
            for rated_food_id, rating in highly_rated.items():
                rated_food = next((f for f in self.food_database if f.food_id == rated_food_id), None)
                if rated_food:
                    similarity = self._calculate_food_similarity(food, rated_food)
                    similarity_score += similarity * (rating / 10.0)
            
            if similarity_score > 0:
                scored_foods[food.food_id] = {
                    "food": food,
                    "score": similarity_score
                }
        
        # Sort by score and return top N
        sorted_foods = sorted(scored_foods.items(), key=lambda x: x[1]["score"], reverse=True)
        
        for food_id, item in sorted_foods[:n]:
            food = item["food"]
            recommendations.append({
                "food_id": food.food_id,
                "name": food.name,
                "category": food.category,
                "calories": food.nutrition_info.calories,
                "protein_g": food.nutrition_info.protein_g,
                "reason": "Similar to meals you enjoyed"
            })
        
        return recommendations
    
    def get_constraint_based_recommendations(self, target_calories: int, 
                                             target_protein: float, n: int = 5) -> List[Dict]:
        """
        Recommend meals that satisfy dietary constraints and goals
        """
        recommendations = []
        
        # Filter foods by dietary restrictions
        suitable_foods = [f for f in self.food_database 
                         if self._satisfies_dietary_constraints(f)]
        
        # Score foods by nutritional fit
        scored_foods = []
        for food in suitable_foods:
            # Calculate how well it balances the remaining daily needs
            remaining_calories = max(target_calories - sum(item.get("calories", 0) 
                                    for item in recommendations), 500)
            
            calorie_fit = 1.0 - abs(food.nutrition_info.calories - remaining_calories) / remaining_calories
            calorie_fit = max(0, min(1.0, calorie_fit))
            
            # Protein fit
            protein_fit = 1.0 - abs(food.nutrition_info.protein_g - (target_protein / 3)) / (target_protein / 3)
            protein_fit = max(0, min(1.0, protein_fit))
            
            # User satisfaction (if known)
            satisfaction = self.user_ratings.get(food.food_id, 5.0) / 10.0
            
            # Combined score
            score = (calorie_fit * 0.4) + (protein_fit * 0.35) + (satisfaction * 0.25)
            
            scored_foods.append((food, score))
        
        # Sort and return top N
        scored_foods.sort(key=lambda x: x[1], reverse=True)
        
        for food, score in scored_foods[:n]:
            recommendations.append({
                "food_id": food.food_id,
                "name": food.name,
                "category": food.category,
                "calories": food.nutrition_info.calories,
                "protein_g": food.nutrition_info.protein_g,
                "macros": food.nutrition_info.get_macro_ratio(),
                "fit_score": round(score, 2),
                "reason": "Matches your daily nutritional targets"
            })
        
        return recommendations
    
    def _satisfies_dietary_constraints(self, food: FoodItem) -> bool:
        """Check if food satisfies user's restrictions"""
        if "vegan" in self.user_profile.dietary_restrictions and not food.is_vegan:
            return False
        if "vegetarian" in self.user_profile.dietary_restrictions and not food.is_vegetarian:
            return False
        if "gluten_free" in self.user_profile.dietary_restrictions and not food.is_gluten_free:
            return False
        
        # Check allergies
        for allergy in self.user_profile.allergies:
            if allergy.lower() in food.tags:
                return False
        
        return True
    
    def _calculate_food_similarity(self, food1: FoodItem, food2: FoodItem) -> float:
        """Calculate similarity between two foods (0-1)"""
        # Category match
        category_match = 1.0 if food1.category == food2.category else 0.5
        
        # Nutritional similarity (macro ratio)
        macros1 = food1.nutrition_info.get_macro_ratio()
        macros2 = food2.nutrition_info.get_macro_ratio()
        
        macro_diff = sum(abs(macros1[k] - macros2[k]) for k in macros1) / 3
        macro_similarity = 1.0 - (macro_diff / 100)
        
        # Tag overlap
        tag_overlap = len(set(food1.tags) & set(food2.tags)) / max(len(set(food1.tags) | set(food2.tags)), 1)
        
        return (category_match * 0.3) + (macro_similarity * 0.5) + (tag_overlap * 0.2)
    
    def _get_default_recommendations(self, n: int) -> List[Dict]:
        """Get generic healthy recommendations"""
        # Filter by constraints, sort by healthiness
        suitable = [f for f in self.food_database if self._satisfies_dietary_constraints(f)]
        
        # Sort by protein content (healthier)
        suitable.sort(key=lambda f: f.nutrition_info.protein_g, reverse=True)
        
        recommendations = []
        for food in suitable[:n]:
            recommendations.append({
                "food_id": food.food_id,
                "name": food.name,
                "category": food.category,
                "calories": food.nutrition_info.calories,
                "protein_g": food.nutrition_info.protein_g,
                "reason": "Nutritious and aligns with your preferences"
            })
        
        return recommendations


class ActivityRecommendationEngine:
    """Recommend study times and exercise based on patterns"""
    
    def __init__(self, user_profile: UserProfile):
        self.user_profile = user_profile
        self.productivity_history: List[int] = []
        self.energy_history: List[int] = []
        self.time_slots: List[int] = []  # Hour of day
    
    def add_productivity_data(self, hour: int, focus_score: int, energy_level: int):
        """Record productivity at specific time"""
        self.time_slots.append(hour)
        self.productivity_history.append(focus_score)
        self.energy_history.append(energy_level)
    
    def recommend_study_times(self, num_recommendations: int = 3) -> List[Dict]:
        """Recommend optimal study times based on history"""
        if not self.productivity_history:
            # Default recommendations
            return [
                {"hour": 10, "reason": "Peak morning focus window", "expected_focus": 9},
                {"hour": 14, "reason": "Post-break recovery focus", "expected_focus": 8},
                {"hour": 17, "reason": "Evening focus peak", "expected_focus": 8}
            ]
        
        # Calculate average productivity per hour
        hour_productivity = {}
        for hour, focus in zip(self.time_slots, self.productivity_history):
            if hour not in hour_productivity:
                hour_productivity[hour] = []
            hour_productivity[hour].append(focus)
        
        hour_averages = {hour: sum(scores) / len(scores) 
                        for hour, scores in hour_productivity.items()}
        
        # Sort by average productivity
        sorted_hours = sorted(hour_averages.items(), key=lambda x: x[1], reverse=True)
        
        recommendations = []
        for hour, avg_focus in sorted_hours[:num_recommendations]:
            recommendations.append({
                "hour": hour,
                "expected_focus": round(avg_focus, 1),
                "reason": f"Your data shows peak focus around {hour}:00"
            })
        
        return recommendations
    
    def recommend_exercise_timing(self) -> Dict:
        """Recommend optimal time for exercise"""
        if not self.energy_history:
            return {
                "recommended_hour": 17,
                "reason": "Late afternoon is typically good for exercise energy levels"
            }
        
        # Find hour with highest energy
        hour_energy = {}
        for hour, energy in zip(self.time_slots, self.energy_history):
            if hour not in hour_energy:
                hour_energy[hour] = []
            hour_energy[hour].append(energy)
        
        hour_avg_energy = {hour: sum(levels) / len(levels) 
                          for hour, levels in hour_energy.items()}
        
        best_hour = max(hour_avg_energy.items(), key=lambda x: x[1])[0]
        
        return {
            "recommended_hour": best_hour,
            "expected_energy_level": round(hour_avg_energy[best_hour], 1),
            "reason": f"Your energy levels peak around {best_hour}:00"
        }
