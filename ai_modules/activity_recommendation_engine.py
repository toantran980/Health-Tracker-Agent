from typing import List, Dict, Optional

from models.user_profile import UserProfile, Goal


class ActivityRecommendationEngine:
    """
    Recommends physical activities based on the user's energy level,
    available time, and active health goals.
    """

    ACTIVITIES = [
        {"name": "Running",            "intensity": 8, "type": "cardio",      "indoor": False, "alt": "Treadmill running"},
        {"name": "Cycling",            "intensity": 7, "type": "cardio",      "indoor": False, "alt": "Stationary bike"},
        {"name": "Swimming",           "intensity": 7, "type": "cardio",      "indoor": True,  "alt": "Swimming"},
        {"name": "HIIT",               "intensity": 9, "type": "cardio",      "indoor": True,  "alt": "HIIT"},
        {"name": "Jump rope",          "intensity": 8, "type": "cardio",      "indoor": True,  "alt": "Jump rope"},
        {"name": "Brisk walking",      "intensity": 4, "type": "cardio",      "indoor": False, "alt": "Treadmill walking"},
        {"name": "Weight training",    "intensity": 7, "type": "strength",    "indoor": True,  "alt": "Weight training"},
        {"name": "Bodyweight circuit", "intensity": 6, "type": "strength",    "indoor": True,  "alt": "Bodyweight circuit"},
        {"name": "Resistance bands",   "intensity": 5, "type": "strength",    "indoor": True,  "alt": "Resistance bands"},
        {"name": "Yoga",               "intensity": 3, "type": "flexibility", "indoor": True,  "alt": "Yoga"},
        {"name": "Stretching",         "intensity": 2, "type": "flexibility", "indoor": True,  "alt": "Stretching"},
        {"name": "Pilates",            "intensity": 4, "type": "flexibility", "indoor": True,  "alt": "Pilates"},
    ]

    def __init__(self, user_profile: UserProfile):
        self.user_profile = user_profile

    def preferred_types(self) -> List[str]:
        """Return activity types ordered by relevance to the user's goal."""
        if Goal.MUSCLE_GAIN in self.user_profile.goals:
            return ["strength", "cardio", "flexibility"]
        if Goal.WEIGHT_LOSS in self.user_profile.goals:
            return ["cardio", "strength", "flexibility"]
        return ["cardio", "strength", "flexibility"]

    def recommend(
        self,
        energy_level: int = 5,
        available_minutes: int = 30,
        weather_hints: Optional[List[str]] = None,
        n: int = 3,
    ) -> List[Dict]:
        """Return up to n activity recommendations."""
        weather_hints = weather_hints or []
        force_indoor = any("indoor" in h.lower() or "rainy" in h.lower() for h in weather_hints)

        max_intensity = max(1, energy_level)
        preferred_types = self.preferred_types()

        scored: List[tuple] = []
        for act in self.ACTIVITIES:
            if act["intensity"] > max_intensity:
                continue

            name = act["alt"] if (force_indoor and not act["indoor"]) else act["name"]

            try:
                type_priority = len(preferred_types) - preferred_types.index(act["type"])
            except ValueError:
                type_priority = 0

            ideal_intensity = max(1, int(energy_level * 0.7))
            intensity_fit = 1.0 - abs(act["intensity"] - ideal_intensity) / 10.0

            score = type_priority + intensity_fit
            scored.append((act, name, score))

        scored.sort(key=lambda x: x[2], reverse=True)

        results = []
        for act, display_name, score in scored[:n]:
            intensity_ratio = act["intensity"] / 10.0
            duration = max(10, int(available_minutes * (1.0 - intensity_ratio * 0.3)))

            results.append({
                "name": display_name,
                "type": act["type"],
                "intensity": act["intensity"],
                "duration_minutes": duration,
                "indoor": act["indoor"] or force_indoor,
                "goal_aligned": act["type"] == preferred_types[0],
                "reason": self.reason(act["type"], energy_level, force_indoor),
            })

        return results

    def reason(self, activity_type: str, energy: int, indoor: bool) -> str:
        parts = []
        if activity_type == "strength":
            parts.append("Supports muscle development")
        elif activity_type == "cardio":
            parts.append("Boosts calorie burn and cardiovascular health")
        else:
            parts.append("Improves flexibility and recovery")

        if energy >= 7:
            parts.append("energy level is high - good time for an intense session")
        elif energy >= 4:
            parts.append("moderate energy - steady effort recommended")
        else:
            parts.append("low energy - light movement aids recovery")

        if indoor:
            parts.append("adjusted for indoor conditions")

        return "; ".join(parts) + "."
