"""Knowledge Base - Rule-based reasoning system"""
from typing import List, Dict, Any
from dataclasses import dataclass
from models.user_profile import UserProfile, Goal
from models.meal import NutritionInfo, Meal
from models.activity import StudySession


@dataclass
class Rule:
    """Represents a if-then rule in the knowledge base"""
    name: str
    condition: callable  # Function that returns boolean
    action: callable    # Function that returns recommendation
    priority: int = 5   # 1-10, higher = higher priority
    confidence: float = 1.0  # 0-1, confidence in this rule


class KnowledgeBase:
    """Rule-based inference engine for health recommendations"""
    
    def __init__(self, user_profile: UserProfile):
        self.user_profile = user_profile
        self.rules: List[Rule] = []
        self.facts: Dict[str, Any] = {}
        self._initialize_rules()
    
    def _initialize_rules(self):
        """Initialize built-in rules for the knowledge base"""
        
        # Rule: If weight loss goal and daily intake > target, recommend calorie reduction
        self.add_rule(Rule(
            name="weight_loss_calorie_reduction",
            condition=lambda: (Goal.WEIGHT_LOSS in self.user_profile.goals and 
                             self.facts.get("daily_calories", 0) > self.user_profile.target_calories * 1.1),
            action=lambda: {
                "type": "nutrition_recommendation",
                "action": "reduce_calorie_intake",
                "suggestion": f"Daily intake exceeds target by {self.facts.get('daily_calories', 0) - self.user_profile.target_calories}kcal. Aim for 300-500kcal deficit for sustainable weight loss.",
                "confidence": 0.95
            },
            priority=9
        ))
        
        # Rule: If muscle gain goal and low protein, recommend protein increase
        self.add_rule(Rule(
            name="muscle_gain_protein",
            condition=lambda: (Goal.MUSCLE_GAIN in self.user_profile.goals and 
                             self.facts.get("daily_protein", 0) < self.user_profile.target_protein_g * 0.85),
            action=lambda: {
                "type": "nutrition_recommendation",
                "action": "increase_protein",
                "suggestion": f"Current protein: {self.facts.get('daily_protein', 0)}g. Target: {self.user_profile.target_protein_g}g. Aim for {self.user_profile.weight_kg * 1.6}g for muscle growth.",
                "confidence": 0.92
            },
            priority=8
        ))
        
        # Rule: If energy optimization goal and low sleep, recommend earlier bedtime
        self.add_rule(Rule(
            name="energy_optimization_sleep",
            condition=lambda: (Goal.ENERGY_OPTIMIZATION in self.user_profile.goals and 
                             self.facts.get("sleep_hours", 0) < 7),
            action=lambda: {
                "type": "lifestyle_recommendation",
                "action": "increase_sleep",
                "suggestion": f"Current sleep: {self.facts.get('sleep_hours', 0)}h. Aim for 7-9 hours for optimal energy levels throughout the day.",
                "confidence": 0.90
            },
            priority=8
        ))
        
        # Rule: If high study difficulty and low energy, suggest splitting sessions
        self.add_rule(Rule(
            name="high_difficulty_low_energy",
            condition=lambda: (self.facts.get("upcoming_difficulty", 0) > 7 and 
                             self.facts.get("energy_level", 5) < 5),
            action=lambda: {
                "type": "schedule_recommendation",
                "action": "split_study_session",
                "suggestion": "Break difficult study tasks into 25-30 min sessions with 5 min breaks. Better focus when energy is lower.",
                "confidence": 0.88
            },
            priority=7
        ))
        
        # Rule: If low macro balance and consistent meal patterns, suggest meal modifications
        self.add_rule(Rule(
            name="macro_imbalance_correction",
            condition=lambda: self.facts.get("macro_balance", "balanced") == "unbalanced",
            action=lambda: {
                "type": "nutrition_recommendation",
                "action": "adjust_meal_macros",
                "suggestion": f"Today's meal balance: {self.facts.get('macro_balance_details', {})}. Recommend adjusting next meal for better macro distribution.",
                "confidence": 0.85
            },
            priority=6
        ))
        
        # Rule: If study session < 25 min and energy high, encourage longer session
        self.add_rule(Rule(
            name="short_session_high_energy",
            condition=lambda: (self.facts.get("recent_session_duration", 0) < 25 and 
                             self.facts.get("energy_level", 5) >= 7),
            action=lambda: {
                "type": "schedule_recommendation",
                "action": "extend_study_session",
                "suggestion": f"Your energy is high (Level {self.facts.get('energy_level', 5)}). Consider extending this study session to 45-50 min to maximize productivity.",
                "confidence": 0.80
            },
            priority=6
        ))
        
        # Rule: If consistent good meals on study days, reinforce the pattern
        self.add_rule(Rule(
            name="positive_nutrition_pattern",
            condition=lambda: (self.facts.get("correlation_nutrition_study", 0) > 0.6 and
                             self.facts.get("adherence_rate", 0) > 0.7),
            action=lambda: {
                "type": "positive_reinforcement",
                "action": "reinforce_meal_pattern",
                "suggestion": "Strong correlation found: high-quality meals → better study focus. Keep up current meal plan!",
                "confidence": 0.85
            },
            priority=7
        ))
    
    def add_rule(self, rule: Rule):
        """Add a rule to the knowledge base"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority, reverse=True)
    
    def add_fact(self, key: str, value: Any):
        """Add a fact to working memory"""
        self.facts[key] = value
    
    def add_facts(self, facts: Dict[str, Any]):
        """Add multiple facts at once"""
        self.facts.update(facts)
    
    def infer(self) -> List[Dict[str, Any]]:
        """Run inference using forward chaining - execute all applicable rules"""
        recommendations = []
        
        for rule in self.rules:
            try:
                if rule.condition():
                    result = rule.action()
                    result["rule_name"] = rule.name
                    result["priority"] = rule.priority
                    recommendations.append(result)
            except Exception as e:
                # Skip rules that fail evaluation
                continue
        
        return recommendations
    
    def get_top_recommendations(self, n: int = 3) -> List[Dict[str, Any]]:
        """Get top N recommendations by priority"""
        recommendations = self.infer()
        return sorted(recommendations, key=lambda r: r.get("priority", 0), reverse=True)[:n]
    
    def clear_facts(self):
        """Clear working memory (facts) for next reasoning cycle"""
        self.facts.clear()
    
    def explain_recommendation(self, recommendation: Dict[str, Any]) -> str:
        """Provide human-readable explanation of why a recommendation was made"""
        rule_name = recommendation.get("rule_name", "unknown")
        return f"Rule '{rule_name}' triggered based on current goals and metrics. {recommendation.get('suggestion', '')}"


class BehavioralAnalyzer:
    """Analyze behavioral patterns and correlations"""
    
    @staticmethod
    def calculate_correlation(data1: List[float], data2: List[float]) -> float:
        """Calculate correlation between two data series"""
        if len(data1) < 2 or len(data1) != len(data2):
            return 0.0
        
        n = len(data1)
        mean1 = sum(data1) / n
        mean2 = sum(data2) / n
        
        numerator = sum((data1[i] - mean1) * (data2[i] - mean2) for i in range(n))
        denom1 = sum((x - mean1) ** 2 for x in data1)
        denom2 = sum((x - mean2) ** 2 for x in data2)
        
        denominator = (denom1 * denom2) ** 0.5
        
        if denominator == 0:
            return 0.0
        return numerator / denominator
    
    @staticmethod
    def detect_anomaly(values: List[float], sensitivity: float = 2.0) -> bool:
        """Detect anomaly using z-score method"""
        if len(values) < 2:
            return False
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return False
        
        latest_z_score = abs((values[-1] - mean) / std_dev)
        return latest_z_score > sensitivity
    
    @staticmethod
    def identify_pattern(values: List[float], threshold: float = 0.7) -> str:
        """Identify trend pattern in data"""
        if len(values) < 3:
            return "insufficient_data"
        
        # Simple trend detection
        increases = sum(1 for i in range(1, len(values)) if values[i] > values[i-1])
        trend_ratio = increases / (len(values) - 1)
        
        if trend_ratio >= threshold:
            return "increasing"
        elif trend_ratio <= (1 - threshold):
            return "decreasing"
        else:
            return "stable"
