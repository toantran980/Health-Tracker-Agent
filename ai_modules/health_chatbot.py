import os
import json
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

client = None
model = None
provider = None

def _init_provider():
    global client, model, provider
    if client is not None:
        return
    if GROQ_API_KEY:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        model = "llama-3.3-70b-versatile"
        provider = "groq"
    else:
        raise EnvironmentError(
            "No AI key found."
        )

    print(f"[Chatbot] Provider: {provider} | Model: {model}")

MAX_HISTORY_PAIRS = 20

# ===========================================================================
# DYNAMIC NUTRITION ENGINE
# ===========================================================================

ACTIVITY_MULTIPLIERS = {
    "sedentary": 13,
    "light": 14,
    "moderate": 15,
    "active": 16,
}

PROTEIN_PER_LB = {
    "weight_loss": 0.9,
    "general_wellness": 0.8,
    "muscle_gain": 1.0,
}

@dataclass
class BodyMetrics:
    weight_lbs: float
    goal: str = "general_wellness"
    activity_level: str = "moderate"

class NutritionEngine:
    @staticmethod
    def calculate_targets(metrics: BodyMetrics):
        weight = metrics.weight_lbs
        goal = metrics.goal
        activity = metrics.activity_level
        base = ACTIVITY_MULTIPLIERS.get(activity, 15)
        calories = weight * base
        if goal == "weight_loss":
            calories -= 400
        elif goal == "muscle_gain":
            calories += 300
        protein = weight * PROTEIN_PER_LB.get(goal, 0.8)
        fat = (calories * 0.25) / 9
        carbs = (calories - (protein * 4 + fat * 9)) / 4
        return {
            "calories": int(calories),
            "protein_g": int(protein),
            "fat_g": int(fat),
            "carbs_g": int(carbs),
        }

# ═══════════════════════════════════════════════════════════════════════════
# USER HEALTH SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class UserHealthSnapshot:
    weight_lbs: float = 150
    health_goal: str = "general_wellness"
    activity_level: str = "moderate"

    calories_today: int = 0
    protein_g: float = 0.0
    carbs_g: float = 0.0
    fat_g: float = 0.0
    water_ml: int = 0
    water_target_ml: int = 2500
    study_hours_today: float = 0.0
    focus_score: Optional[float] = None
    sleep_hours_last_night: Optional[float] = None
    weekly_adherence_pct: Optional[float] = None
    dietary_restrictions: list[str] = field(default_factory=list)
    active_insights: list[str] = field(default_factory=list)

    def to_context_block(self) -> str:
        metrics = BodyMetrics(
            weight_lbs=self.weight_lbs,
            goal=self.health_goal,
            activity_level=self.activity_level,
        )
        targets = NutritionEngine.calculate_targets(metrics)
        lines = [
            f"- Health goal: {self.health_goal}",
            f"- Body weight: {self.weight_lbs} lbs",
            f"- Calories today: {self.calories_today} / {targets['calories']} kcal",
            f"- Protein: {self.protein_g}g / {targets['protein_g']}g target",
            f"- Carbs: {self.carbs_g}g / Fat: {self.fat_g}g",
            f"- Water: {self.water_ml}ml / {self.water_target_ml}ml target",
            f"- Study hours today: {self.study_hours_today}h",
        ]
        if self.focus_score is not None:
            lines.append(f"- Focus score: {self.focus_score}/10")
        if self.sleep_hours_last_night is not None:
            lines.append(f"- Sleep last night: {self.sleep_hours_last_night}h")
        if self.weekly_adherence_pct is not None:
            lines.append(f"- Weekly adherence: {self.weekly_adherence_pct}%")
        if self.dietary_restrictions:
            lines.append(f"- Dietary restrictions: {', '.join(self.dietary_restrictions)}")
        if self.active_insights:
            lines.append("- Recent AI insights:")
            for insight in self.active_insights:
                lines.append(f"    {insight}")
        return "\n".join(lines)

# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT 
# ═══════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT_TEMPLATE = """You are VitaAI, a smart and friendly AI assistant
inside a health and wellness tracker app.

A health snapshot is provided below for context. Use it only when relevant.

Health snapshot:
{health_context}

Guidelines:
- General questions → answer based on the question only
- Personal questions → use snapshot
- Health/medical → never diagnose, always suggest consulting a professional
- Dietary restrictions → respect them
- Tone: warm and concise
"""

# ═══════════════════════════════════════════════════════════════════════════
# CHATBOT CLASS
# ═══════════════════════════════════════════════════════════════════════════

class HealthChatbot:
    def __init__(self, snapshot: UserHealthSnapshot):
        self.snapshot = snapshot
        self.history: list[dict] = []

    def chat(self, user_message: str) -> str:
        _init_provider()
        self.history.append({"role": "user", "content": user_message})
        self._trim_history()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            health_context=self.snapshot.to_context_block()
        )

        try:
            if provider == "openai":
                response = client.ChatCompletion.create(
                    model=model,
                    messages=[{"role": "system", "content": system_prompt}, *self.history],
                    max_tokens=512
                )
                reply = response.choices[0].message.content.strip()
            else:  # groq
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=512,
                    messages=[{"role": "system", "content": system_prompt}, *self.history]
                )
                reply = response.choices[0].message.content.strip()
        except Exception as e:
            self.history.pop()
            print(f"[Chatbot] API error ({provider}): {e}")
            reply = "I'm having trouble connecting. Please try again."

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self):
        self.history = []

    def _trim_history(self):
        max_messages = MAX_HISTORY_PAIRS * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]

# ═══════════════════════════════════════════════════════════════════════════
# QUICK TEST
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    snapshot = UserHealthSnapshot(
        weight_lbs=200,
        health_goal="maintenance",
        activity_level="moderate",
        calories_today=2100,
        protein_g=120,
        carbs_g=250,
        fat_g=70,
        study_hours_today=4,
        focus_score=7.5,
        sleep_hours_last_night=6.5,
        weekly_adherence_pct=70,
        dietary_restrictions=["vegetarian"],
        active_insights=["High protein days boost next-day focus"]
    )

    bot = HealthChatbot(snapshot)
    print(f"\nVitaAI ready ({provider}). Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        print(f"\nVitaAI: {bot.chat(user_input)}\n")