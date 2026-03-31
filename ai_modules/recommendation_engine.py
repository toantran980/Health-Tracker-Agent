import math
from typing import List, Dict, Optional
from datetime import datetime
from models.user_profile import UserProfile, Goal
from models.meal import FoodItem, NutritionInfo


# ---------------------------------------------------------------------------
# Goal-specific weights
# Each weight tuple: (calories, protein, carbs, fat, satisfaction)
# Must sum to 1.0 across the first four + satisfaction.
# ---------------------------------------------------------------------------
GOAL_WEIGHTS: Dict[str, Dict[str, float]] = {
    "MUSCLE_GAIN": {"calories": 0.15, "protein": 0.55, "carbs": 0.10, "fat": 0.10, "satisfaction": 0.10},
    "WEIGHT_LOSS": {"calories": 0.50, "protein": 0.20, "carbs": 0.10, "fat": 0.10, "satisfaction": 0.10},
    "MAINTENANCE": {"calories": 0.20, "protein": 0.25, "carbs": 0.20, "fat": 0.15, "satisfaction": 0.20},
}
DEFAULT_WEIGHTS = {"calories": 0.20, "protein": 0.25, "carbs": 0.20, "fat": 0.15, "satisfaction": 0.20}


class MealRecommendationEngine:
    """
    Personalized meal suggestions using content-based filtering and
    vector-space similarity with goal-aware heuristic weighting.

    AI logic overview
    -----------------
    1. Hard filtering:   drop foods that violate dietary constraints / allergies.
    2. Vectorisation:    represent each food as a 4-D normalised macro vector
                         [calories, protein_g, carbs_g, fat_g].
    3. Cosine scoring:   measure angular distance between food vector and
                         user target / liked-food vectors (scale-independent).
    4. Goal weighting:   each macro dimension's contribution to the final
                         score shifts according to the user's active Goal
                         (reasoning adapts to user context).
    5. Satisfaction:     user ratings (1-10) blend into the final score so
                         palatability is never ignored.
    """

    def __init__(self, user_profile: UserProfile, food_database: List[FoodItem]):
        self.user_profile   = user_profile
        self.food_database  = food_database
        self.user_meal_history: List[Dict] = []
        self.user_ratings:      Dict[str, float] = {}   # food_id -> rating (1-10)

        # Pre-compute per-feature min/max across the whole database once so
        # normalisation is consistent for every call.
        self.db_stats = self.compute_db_stats()

    # ------------------------------------------------------------------ #
    #  Public data-ingestion methods                                        #
    # ------------------------------------------------------------------ #

    def rate_meal(self, food_id: str, rating: float) -> None:
        """Store a user rating (1-10) for a given food."""
        if not 1.0 <= rating <= 10.0:
            raise ValueError("Rating must be between 1 and 10.")
        self.user_ratings[food_id] = rating

    def add_meal_to_history(self, food_id: str, meal_type: str) -> None:
        """Log a consumed meal with timestamp."""
        self.user_meal_history.append({
            "food_id":   food_id,
            "meal_type": meal_type,
            "timestamp": datetime.now(),
        })

    # ------------------------------------------------------------------ #
    #  Vector helpers                                                       #
    # ------------------------------------------------------------------ #

    def compute_db_stats(self) -> Dict[str, Dict[str, float]]:
        """
        Pre-compute per-feature (min, max) across the whole food database.

        Used for min-max normalisation so that calorie values (~2 000) do not
        swamp protein values (~30 g) when cosine similarity is computed.
        """
        if not self.food_database:
            return {}

        fields = ["calories", "protein_g", "carbs_g", "fat_g"]
        stats: Dict[str, Dict[str, float]] = {}
        for field in fields:
            values = [getattr(f.nutrition_info, field) for f in self.food_database]
            stats[field] = {"min": min(values), "max": max(values)}
        return stats

    def food_to_raw_vector(self, info: NutritionInfo) -> List[float]:
        """Return raw 4-D macro vector."""
        return [info.calories, info.protein_g, info.carbs_g, info.fat_g]

    def minmax_normalize(self, vec: List[float]) -> List[float]:
        """
        Min-max normalise a 4-D macro vector to [0, 1] per feature using
        database-wide statistics computed at construction time.

        Without this step, cosine similarity is dominated by whichever
        feature has the largest absolute values (almost always calories).
        """
        fields = ["calories", "protein_g", "carbs_g", "fat_g"]
        normalised = []
        for i, field in enumerate(fields):
            mn  = self.db_stats.get(field, {}).get("min", 0)
            mx  = self.db_stats.get(field, {}).get("max", 1)
            val = (vec[i] - mn) / (mx - mn) if mx != mn else 0.0
            normalised.append(val)
        return normalised

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """
        Cosine similarity between two pre-normalised vectors.

        Returns a value in [0, 1]; returns 0 for zero-magnitude inputs.
        """
        dot   = sum(a * b for a, b in zip(v1, v2))
        mag_a = math.sqrt(sum(a ** 2 for a in v1))
        mag_b = math.sqrt(sum(b ** 2 for b in v2))
        return dot / (mag_a * mag_b) if mag_a > 0 and mag_b > 0 else 0.0

    def food_vector(self, food: FoodItem) -> List[float]:
        """Return a min-max normalised 4-D vector for a food item."""
        return self.minmax_normalize(self.food_to_raw_vector(food.nutrition_info))

    def target_vector(self, target_calories: float, target_protein: float,
                       target_carbs: float = 0.0, target_fat: float = 0.0) -> List[float]:
        """Return a min-max normalised target vector."""
        raw = [target_calories, target_protein, target_carbs, target_fat]
        return self.minmax_normalize(raw)

    # ------------------------------------------------------------------ #
    #  Goal-weight resolution                                              #
    # ------------------------------------------------------------------ #

    def resolve_weights(self) -> Dict[str, float]:
        """
        Return the weight dict that matches the user's active Goal.

        Falls back to balanced default when no recognised goal is set.
        """
        if Goal.MUSCLE_GAIN in self.user_profile.goals:
            return GOAL_WEIGHTS["MUSCLE_GAIN"]
        if Goal.WEIGHT_LOSS in self.user_profile.goals:
            return GOAL_WEIGHTS["WEIGHT_LOSS"]
        return DEFAULT_WEIGHTS

    # ------------------------------------------------------------------ #
    #  Constraint check                                                     #
    # ------------------------------------------------------------------ #

    def satisfies_dietary_constraints(self, food: FoodItem) -> bool:
        """Return True iff the food respects all profile restrictions."""
        restrictions = self.user_profile.dietary_restrictions
        if "vegan"       in restrictions and not food.is_vegan:       return False
        if "vegetarian"  in restrictions and not food.is_vegetarian:  return False
        if "gluten_free" in restrictions and not food.is_gluten_free: return False

        food_tags_lower = {t.lower() for t in food.tags}
        for allergy in self.user_profile.allergies:
            if allergy.lower() in food_tags_lower:
                return False
        return True

    # ------------------------------------------------------------------ #
    #  Recommendation methods                                              #
    # ------------------------------------------------------------------ #

    def get_content_based_recommendations(self, n: int = 5) -> List[Dict]:
        """
        Content-based filtering: recommend foods similar to highly-rated ones.

        For each candidate food, compute cosine similarity (in 4-D normalised
        macro space) against every food the user rated >= 7.  Weight each
        similarity by the normalised rating so better-liked foods exert more
        influence.  Sum across all liked foods, sort descending.

        Falls back to high-protein defaults when no ratings exist.
        """
        if not self.user_ratings:
            return self.get_default_recommendations(n)

        liked = {fid: r for fid, r in self.user_ratings.items() if r >= 7.0}
        if not liked:
            return self.get_default_recommendations(n)

        # Build a lookup map once for efficiency
        food_by_id: Dict[str, FoodItem] = {f.food_id: f for f in self.food_database}

        scored: Dict[str, Dict] = {}
        for food in self.food_database:
            if food.food_id in liked:
                continue   # skip already-rated foods                  
            if not self.satisfies_dietary_constraints(food):
                continue

            fv = self.food_vector(food)
            total_sim = 0.0

            for rated_id, rating in liked.items():
                rated_food = food_by_id.get(rated_id)
                if rated_food is None:
                    continue
                rv  = self.food_vector(rated_food)
                sim = self.cosine_similarity(fv, rv)
                total_sim += sim * (rating / 10.0)   # rating-weighted similarity

            if total_sim > 0:
                scored[food.food_id] = {"food": food, "score": total_sim}

        ranked = sorted(scored.values(), key=lambda x: x["score"], reverse=True)
        return [
            {
                "food_id":  item["food"].food_id,
                "name":     item["food"].name,
                "calories": item["food"].nutrition_info.calories,
                "score":    round(item["score"], 4),
                "reason":   "Similar macro profile to meals you rated highly",
            }
            for item in ranked[:n]
        ]

    def get_constraint_based_recommendations(
        self,
        target_calories: float,
        target_protein:  float,
        target_carbs:    float = 0.0,
        target_fat:      float = 0.0,
        n: int = 5,
    ) -> List[Dict]:
        """
        Goal-aware constraint-based recommendations.
        Each macro is scored independently as:

            fit_k = 1 − |actual_k − target_k| / target_k    (clamped to 0)

        The four macro-fit scores and a satisfaction score are then combined
        using goal-specific weights that sum to 1.0.

        For MUSCLE_GAIN, protein weight jumps to 0.55.
        For WEIGHT_LOSS, calorie weight becomes 0.50.
        For balanced/maintenance, weights are roughly equal.
        """
        weights = self.resolve_weights()
        tv      = self.target_vector(target_calories, target_protein, target_carbs, target_fat)

        targets = {
            "calories":  target_calories,
            "protein_g": target_protein,
            "carbs_g":   target_carbs,
            "fat_g":     target_fat,
        }

        def macro_fit(actual: float, target: float) -> float:
            """Normalised proximity score in [0, 1]."""
            if target == 0:
                return 1.0
            return max(0.0, 1.0 - abs(actual - target) / target)

        scored: List[tuple] = []
        for food in self.food_database:
            if not self.satisfies_dietary_constraints(food):
                continue

            ni = food.nutrition_info

            # Individual macro-fit scores
            cal_fit  = macro_fit(ni.calories,  targets["calories"])
            prot_fit = macro_fit(ni.protein_g, targets["protein_g"])
            carb_fit = macro_fit(ni.carbs_g,   targets["carbs_g"])   if targets["carbs_g"]  > 0 else 1.0
            fat_fit  = macro_fit(ni.fat_g,     targets["fat_g"])     if targets["fat_g"]    > 0 else 1.0

            # User satisfaction (default neutral 5/10 when unrated)
            satisfaction = self.user_ratings.get(food.food_id, 5.0) / 10.0

            # Weighted composite score
            score = (
                weights["calories"]     * cal_fit  +
                weights["protein"]      * prot_fit +
                weights["carbs"]        * carb_fit +
                weights["fat"]          * fat_fit  +
                weights["satisfaction"] * satisfaction
            )

            # Also compute cosine similarity for display purposes
            fv      = self.food_vector(food)
            cos_sim = self.cosine_similarity(fv, tv)

            scored.append((food, score, cos_sim))

        scored.sort(key=lambda x: x[1], reverse=True)

        active_goal = (
            "MUSCLE_GAIN" if Goal.MUSCLE_GAIN in self.user_profile.goals
            else "WEIGHT_LOSS" if Goal.WEIGHT_LOSS in self.user_profile.goals
            else "MAINTENANCE"
        )

        return [
            {
                "name":             food.name,
                "food_id":          food.food_id,
                "calories":         food.nutrition_info.calories,
                "protein_g":        food.nutrition_info.protein_g,
                "fit_score":        round(score,   4),
                "cosine_sim":       round(cos_sim, 4),
                "goal_applied":     active_goal,
                "reason":           f"Optimised for {active_goal.lower().replace('_', ' ')} targets",
            }
            for food, score, cos_sim in scored[:n]
        ]

    def get_hybrid_recommendations(
        self,
        target_calories: float,
        target_protein:  float,
        target_carbs:    float = 0.0,
        target_fat:      float = 0.0,
        content_weight:  float = 0.4,
        constraint_weight: float = 0.6,
        n: int = 5,
    ) -> List[Dict]:
        """
        Hybrid recommender: blend content-based and constraint-based scores.

        Combines personalisation (what the user historically likes) with
        nutritional fit (what serves their current targets/goal), giving a
        more robust recommendation than either method alone.

        content_weight:    Weight for content-based score (0-1).
        constraint_weight: Weight for constraint-based score (0-1).
                            content_weight + constraint_weight should = 1.0.

        Returns top-n foods ranked by blended score.
        """
        content_recs    = {r["food_id"]: r["score"] for r in self.get_content_based_recommendations(n=len(self.food_database))}
        constraint_recs = {r["food_id"]: r["fit_score"] for r in self.get_constraint_based_recommendations(target_calories, target_protein, target_carbs, target_fat, n=len(self.food_database))}

        all_ids = set(content_recs) | set(constraint_recs)
        blended: List[tuple] = []
        food_by_id = {f.food_id: f for f in self.food_database}

        for fid in all_ids:
            c_score  = content_recs.get(fid, 0.0)
            cs_score = constraint_recs.get(fid, 0.0)
            combined = content_weight * c_score + constraint_weight * cs_score
            food     = food_by_id.get(fid)
            if food:
                blended.append((food, combined))

        blended.sort(key=lambda x: x[1], reverse=True)
        return [
            {
                "name":        food.name,
                "food_id":     food.food_id,
                "calories":    food.nutrition_info.calories,
                "blend_score": round(score, 4),
                "reason":      "Matches your taste preferences and nutrition targets",
            }
            for food, score in blended[:n]
        ]

    # ------------------------------------------------------------------ #
    #  Default / fallback                                                   #
    # ------------------------------------------------------------------ #

    def get_default_recommendations(self, n: int) -> List[Dict]:
        """
        Cold-start fallback: return constraint-compliant, high-protein foods.

        Used when the user has no ratings yet.
        """
        suitable = [
            f for f in self.food_database
            if self.satisfies_dietary_constraints(f)
        ]
        suitable.sort(key=lambda f: f.nutrition_info.protein_g, reverse=True)
        return [
            {
                "name":      f.name,
                "food_id":   f.food_id,
                "calories":  f.nutrition_info.calories,
                "protein_g": f.nutrition_info.protein_g,
                "reason":    "High-protein recommendation (no rating history yet)",
            }
            for f in suitable[:n]
        ]