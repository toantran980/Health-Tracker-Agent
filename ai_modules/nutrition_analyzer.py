"""Nutrition Analyzer - Pattern recognition and nutritional analysis"""
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from models.meal import DailyNutritionLog, NutritionInfo, Meal


class NutritionAnalyzer:
    """Analyze nutritional patterns and provide insights"""
    
    def __init__(self, target_nutrition: NutritionInfo):
        self.target_nutrition = target_nutrition
        self.history: List[DailyNutritionLog] = []
    
    def add_daily_log(self, log: DailyNutritionLog):
        """Add a daily nutrition log to history"""
        self.history.append(log)
    
    def get_weekly_average(self, days: int = 7) -> NutritionInfo:
        """Calculate average nutrition over last N days"""
        if not self.history:
            return NutritionInfo(0, 0, 0, 0)
        
        recent_logs = self.history[-days:]
        n = len(recent_logs)
        
        total_calories = sum(log.get_total_nutrition().calories for log in recent_logs)
        total_protein = sum(log.get_total_nutrition().protein_g for log in recent_logs)
        total_carbs = sum(log.get_total_nutrition().carbs_g for log in recent_logs)
        total_fat = sum(log.get_total_nutrition().fat_g for log in recent_logs)
        
        return NutritionInfo(
            calories=total_calories / n,
            protein_g=total_protein / n,
            carbs_g=total_carbs / n,
            fat_g=total_fat / n
        )
    
    def calculate_adherence_rate(self, days: int = 7) -> float:
        """Calculate percentage of days that met nutrition targets (±10%)"""
        if not self.history:
            return 0.0
        
        recent_logs = self.history[-days:]
        adherent_days = sum(1 for log in recent_logs if log.get_adherence_ratio(self.target_nutrition) >= 0.9)
        
        return (adherent_days / len(recent_logs)) * 100 if recent_logs else 0.0
    
    def identify_meal_patterns(self) -> Dict[str, any]:
        """Identify recurring meal patterns"""
        patterns = {
            "favorite_meals": {},
            "meal_timing": {},
            "macro_preferences": "unknown"
        }
        
        # Track meal frequency
        meal_counts = {}
        for log in self.history:
            for meal in log.meals:
                for food in meal.food_items:
                    meal_counts[food.name] = meal_counts.get(food.name, 0) + 1
        
        # Get top meals
        patterns["favorite_meals"] = dict(sorted(meal_counts.items(), key=lambda x: x[1], reverse=True)[:5])
        
        # Analyze meal timing patterns
        for log in self.history:
            for meal in log.meals:
                meal_type = meal.meal_type.value
                patterns["meal_timing"][meal_type] = patterns["meal_timing"].get(meal_type, [])
                patterns["meal_timing"][meal_type].append(meal.timestamp.hour)
        
        # Get average meal times
        for meal_type in patterns["meal_timing"]:
            hours = patterns["meal_timing"][meal_type]
            avg_hour = sum(hours) / len(hours) if hours else 0
            patterns["meal_timing"][meal_type] = int(avg_hour)
        
        # Determine macro preference
        weekly_avg = self.get_weekly_average()
        macros = weekly_avg.get_macro_ratio()
        if macros["protein_percent"] > 35:
            patterns["macro_preferences"] = "high_protein"
        elif macros["carbs_percent"] > 55:
            patterns["macro_preferences"] = "high_carb"
        else:
            patterns["macro_preferences"] = "balanced"
        
        return patterns
    
    def detect_nutritional_anomalies(self, sensitivity: float = 2.0) -> List[Dict]:
        """Detect unusual eating patterns"""
        anomalies = []
        
        if len(self.history) < 3:
            return anomalies
        
        recent_calories = [log.get_total_nutrition().calories for log in self.history[-7:]]
        mean_calories = sum(recent_calories) / len(recent_calories)
        variance = sum((x - mean_calories) ** 2 for x in recent_calories) / len(recent_calories)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return anomalies
        
        for i, log in enumerate(self.history[-7:]):
            z_score = abs((log.get_total_nutrition().calories - mean_calories) / std_dev)
            if z_score > sensitivity:
                anomalies.append({
                    "date": log.date,
                    "calories": log.get_total_nutrition().calories,
                    "z_score": z_score,
                    "type": "unusual_caloric_intake"
                })
        
        return anomalies
    
    def get_macro_recommendations(self) -> Dict[str, str]:
        """Get recommendations based on macro analysis"""
        recent_avg = self.get_weekly_average(7)
        target_macros = self.target_nutrition.get_macro_ratio()
        recent_macros = recent_avg.get_macro_ratio()
        
        recommendations = {}
        
        # Protein check
        if recent_macros["protein_percent"] < target_macros["protein_percent"] - 5:
            recommendations["protein"] = f"Increase protein: currently {recent_macros['protein_percent']:.1f}%, target {target_macros['protein_percent']:.1f}%"
        elif recent_macros["protein_percent"] > target_macros["protein_percent"] + 5:
            recommendations["protein"] = f"Reduce protein: currently {recent_macros['protein_percent']:.1f}%, target {target_macros['protein_percent']:.1f}%"
        else:
            recommendations["protein"] = "Protein intake is on target"
        
        # Carbs check
        if recent_macros["carbs_percent"] < target_macros["carbs_percent"] - 5:
            recommendations["carbs"] = f"Increase carbs: currently {recent_macros['carbs_percent']:.1f}%, target {target_macros['carbs_percent']:.1f}%"
        elif recent_macros["carbs_percent"] > target_macros["carbs_percent"] + 5:
            recommendations["carbs"] = f"Reduce carbs: currently {recent_macros['carbs_percent']:.1f}%, target {target_macros['carbs_percent']:.1f}%"
        else:
            recommendations["carbs"] = "Carb intake is on target"
        
        # Fat check
        if recent_macros["fat_percent"] < target_macros["fat_percent"] - 5:
            recommendations["fat"] = f"Increase fats: currently {recent_macros['fat_percent']:.1f}%, target {target_macros['fat_percent']:.1f}%"
        elif recent_macros["fat_percent"] > target_macros["fat_percent"] + 5:
            recommendations["fat"] = f"Reduce fats: currently {recent_macros['fat_percent']:.1f}%, target {target_macros['fat_percent']:.1f}%"
        else:
            recommendations["fat"] = "Fat intake is on target"
        
        return recommendations
    
    def correlate_nutrition_performance(self, performance_scores: List[int]) -> float:
        """
        Calculate correlation between nutrition adherence and performance
        
        Args:
            performance_scores: List of daily performance scores (1-10)
        
        Returns:
            Correlation coefficient (-1 to 1)
        """
        if len(self.history) < 2 or len(performance_scores) != len(self.history):
            return 0.0
        
        # Calculate adherence scores for each day
        adherence_scores = [
            log.get_adherence_ratio(self.target_nutrition)
            for log in self.history
        ]
        
        return self._pearson_correlation(adherence_scores, performance_scores)
    
    def _pearson_correlation(self, x: List[float], y: List[float]) -> float:
        """Calculate Pearson correlation coefficient"""
        if len(x) < 2 or len(x) != len(y):
            return 0.0
        
        n = len(x)
        mean_x = sum(x) / n
        mean_y = sum(y) / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denom_x = sum((xi - mean_x) ** 2 for xi in x)
        denom_y = sum((yi - mean_y) ** 2 for yi in y)
        
        denominator = (denom_x * denom_y) ** 0.5
        
        if denominator == 0:
            return 0.0
        return numerator / denominator
    
    def get_nutrition_report(self) -> Dict:
        """Generate comprehensive nutrition report"""
        return {
            "weekly_average": {
                "calories": round(self.get_weekly_average().calories, 1),
                "protein_g": round(self.get_weekly_average().protein_g, 1),
                "carbs_g": round(self.get_weekly_average().carbs_g, 1),
                "fat_g": round(self.get_weekly_average().fat_g, 1),
            },
            "adherence_rate": round(self.calculate_adherence_rate(), 1),
            "patterns": self.identify_meal_patterns(),
            "anomalies": self.detect_nutritional_anomalies(),
            "recommendations": self.get_macro_recommendations()
        }
