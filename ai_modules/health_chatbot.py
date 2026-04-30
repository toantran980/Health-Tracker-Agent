"""
chatbot.py  →  ai_modules/chatbot.py

AI Health Chatbot powered by Groq (free).
Get your key at: https://console.groq.com

Install:  pip install groq python-dotenv
.env:     GROQ_API_KEY=gsk_...
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

client   = None
model    = None
provider = None

def init_provider():
    global client, model, provider
    if client is not None:
        return
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY not found. Add it to your .env file.\n"
            "Get a free key at: https://console.groq.com"
        )
    from groq import Groq
    client   = Groq(api_key=GROQ_API_KEY)
    model    = "llama-3.3-70b-versatile"
    provider = "groq"
    print(f"[Chatbot] Provider: {provider}  |  Model: {model}")


MAX_HISTORY_PAIRS = 20


# Nutrition engine

ACTIVITY_MULTIPLIERS  = {"sedentary": 13, "light": 14, "moderate": 15, "active": 16, "very_active": 17}
PROTEIN_PER_LB        = {"weight_loss": 0.9, "muscle_gain": 1.0, "general_wellness": 0.8, "maintenance": 0.8}
GOAL_CALORIE_ADJUST   = {"weight_loss": -400, "muscle_gain": 300, "general_wellness": 0, "maintenance": 0}


@dataclass
class BodyMetrics:
    weight_lbs:     float
    goal:           str = "general_wellness"
    activity_level: str = "moderate"


class NutritionEngine:
    @staticmethod
    def calculate_targets(m: BodyMetrics) -> dict:
        calories = m.weight_lbs * ACTIVITY_MULTIPLIERS.get(m.activity_level, 15) + GOAL_CALORIE_ADJUST.get(m.goal, 0)
        protein  = m.weight_lbs * PROTEIN_PER_LB.get(m.goal, 0.8)
        fat      = (calories * 0.25) / 9
        carbs    = max((calories - protein * 4 - fat * 9) / 4, 50)
        return {"calories": int(calories), "protein_g": int(protein), "fat_g": int(fat), "carbs_g": int(carbs)}

    @staticmethod
    def summary(m: BodyMetrics) -> str:
        t = NutritionEngine.calculate_targets(m)
        return f"{t['calories']} kcal | P:{t['protein_g']}g | C:{t['carbs_g']}g | F:{t['fat_g']}g"


# User health snapshot

@dataclass
class UserHealthSnapshot:
    name:           str   = "User"
    weight_lbs:     float = 150.0
    health_goal:    str   = "general_wellness"
    activity_level: str   = "moderate"

    calories_today:  int   = 0
    protein_g:       float = 0.0
    carbs_g:         float = 0.0
    fat_g:           float = 0.0
    water_ml:        int   = 0
    water_target_ml: int   = 2500

    study_hours_today:      float           = 0.0
    focus_score:            Optional[float] = None
    sleep_hours_last_night: Optional[float] = None
    weekly_adherence_pct:   Optional[float] = None

    dietary_restrictions: list[str] = field(default_factory=list)
    active_insights:      list[str] = field(default_factory=list)

    def get_targets(self) -> dict:
        return NutritionEngine.calculate_targets(
            BodyMetrics(self.weight_lbs, self.health_goal, self.activity_level)
        )

    def to_context_block(self) -> str:
        t = self.get_targets()
        lines = [
            f"- Name: {self.name}",
            f"- Weight: {self.weight_lbs}lbs | Goal: {self.health_goal.replace('_',' ')} | Activity: {self.activity_level}",
            f"- Targets: {t['calories']}kcal | P:{t['protein_g']}g | C:{t['carbs_g']}g | F:{t['fat_g']}g",
            f"- Today:   {self.calories_today}kcal | P:{self.protein_g}g | C:{self.carbs_g}g | F:{self.fat_g}g",
            f"- Water: {self.water_ml}ml / {self.water_target_ml}ml | Study: {self.study_hours_today}h",
        ]
        if self.focus_score is not None:
            lines.append(f"- Focus: {self.focus_score}/10")
        if self.sleep_hours_last_night is not None:
            lines.append(f"- Sleep: {self.sleep_hours_last_night}h")
        if self.weekly_adherence_pct is not None:
            lines.append(f"- Adherence: {self.weekly_adherence_pct:.0f}%")
        if self.dietary_restrictions:
            lines.append(f"- Restrictions: {', '.join(self.dietary_restrictions)}")
        if self.active_insights:
            lines.append("- Insights: " + " | ".join(self.active_insights))
        return "\n".join(lines)


# System prompt

SYSTEM_PROMPT_TEMPLATE = """You are VitaAI, a friendly AI assistant in a health and wellness tracker. \
You can help with anything — health, nutrition, study, coding, or general chat.

User snapshot (use only when the question is clearly about the user's own data):
{health_context}

GOAL SETUP: If the user asks to set up goals or calculate their macros, \
ask these one at a time: (1) weight, (2) goal — weight loss / muscle gain / maintain, \
(3) activity — sedentary / light / moderate / active. Then calculate:
  calories = weight_lbs × multiplier ± adjustment
    multipliers: sedentary=13, light=14, moderate=15, active=16
    adjustments: weight_loss=-400, muscle_gain=+300, maintain=0
  protein_g = weight_lbs × rate  (loss=0.9, gain=1.0, maintain=0.8)
  fat_g     = (calories × 0.25) / 9
  carbs_g   = (calories - protein×4 - fat×9) / 4  (min 50g)
Show results clearly and note they are personalized to their body — not generic defaults.

Rules: warm and concise tone | never diagnose | respect dietary restrictions | \
use snapshot only for personal questions, ignore it for general ones."""


# Chatbot class

class HealthChatbot:
    """
    Stateful per-user chatbot. One instance per user in bot_sessions.

    Usage:
        bot = HealthChatbot(snapshot)
        reply = bot.chat("set up my personal goals")
    """

    def __init__(self, snapshot: UserHealthSnapshot):
        self.snapshot = snapshot
        self.history: list[dict] = []

    def chat(self, user_message: str) -> str:
        init_provider()
        self.history.append({"role": "user", "content": user_message})
        self._trim_history()

        try:
            response = client.chat.completions.create(
                model      = model,
                max_tokens = 512,
                messages   = [
                    {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.format(
                        health_context=self.snapshot.to_context_block()
                    )},
                    *self.history,
                ],
            )
            reply = response.choices[0].message.content.strip()
        except Exception as e:
            self.history.pop()
            print(f"[Chatbot] Error: {e}")
            reply = "I'm having trouble connecting right now. Please try again."

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def update_snapshot(self, snapshot: UserHealthSnapshot) -> None:
        """Call after user logs a meal or activity to keep context fresh."""
        self.snapshot = snapshot

    def reset(self) -> None:
        """Clear conversation history, keep snapshot."""
        self.history = []

    def get_provider(self) -> str:
        return provider or "none"

    def _trim_history(self) -> None:
        max_messages = MAX_HISTORY_PAIRS * 2
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]


if __name__ == "__main__":
    snapshot = UserHealthSnapshot(
        name           = "Test User",
        weight_lbs     = 200,
        health_goal    = "general_wellness",
        activity_level = "moderate",
        calories_today = 2100,
        protein_g      = 120,
        carbs_g        = 250,
        fat_g          = 70,
        water_ml       = 1500,
        study_hours_today      = 4.0,
        focus_score            = 7.5,
        sleep_hours_last_night = 6.5,
        weekly_adherence_pct   = 70,
        dietary_restrictions   = ["no pork"],
        active_insights        = ["High protein days boost next-day focus"],
    )

    t = snapshot.get_targets()
    print(f"\n200lb user targets: {NutritionEngine.summary(BodyMetrics(200, 'general_wellness', 'moderate'))}")

    bot = HealthChatbot(snapshot)
    print(f"VitaAI ready ({bot.get_provider()}). Type 'quit' to exit.")
    print("Try: 'set up my personal goals'\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue
        print(f"\nVitaAI: {bot.chat(user_input)}\n")