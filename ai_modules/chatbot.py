"""
chatbot.py

AI Health Chatbot — uses OpenAI (gpt-4o-mini) as primary.
Falls back to Groq (llama-3.3-70b, free tier) if no OpenAI key.

Install:  pip install openai groq python-dotenv
"""

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# AUTO-SELECT PROVIDER
# Set OPENAI_API_KEY in .env to use OpenAI.
# Set GROQ_API_KEY in .env to use Groq (free).
# OpenAI takes priority if both are present.
# ─────────────────────────────────────────────

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")

if OPENAI_API_KEY:
    from openai import OpenAI
    _client   = OpenAI(api_key=OPENAI_API_KEY)
    _model    = "gpt-4o-mini"
    _provider = "openai"
elif GROQ_API_KEY:
    from groq import Groq
    _client   = Groq(api_key=GROQ_API_KEY)
    _model    = "llama-3.3-70b-versatile"
    _provider = "groq"
else:
    raise EnvironmentError(
        "No AI key found.\n"
        "Add OPENAI_API_KEY or GROQ_API_KEY to your .env file.\n"
        "Get a free Groq key at: https://console.groq.com"
    )

print(f"[Chatbot] Provider: {_provider}  |  Model: {_model}")


# ─────────────────────────────────────────────
# USER HEALTH SNAPSHOT
# Fill this from your existing DB before calling chat()
# ─────────────────────────────────────────────

@dataclass
class UserHealthSnapshot:
    """
    Represents the user's current health state.
    Pass real values from your database — only fields you track are needed.
    Missing/None fields are simply omitted from the AI context.
    """
    name: str = "User"

    # Diet
    calories_today: int = 0
    calorie_target: int = 2300
    protein_g: float = 0
    protein_target_g: float = 150
    carbs_g: float = 0
    fat_g: float = 0
    water_ml: int = 0
    water_target_ml: int = 2500

    # Study & focus
    study_hours_today: float = 0
    focus_score: float | None = None          # 1–10 scale

    # Wellness
    sleep_hours_last_night: float | None = None
    weekly_adherence_pct: float | None = None

    # Goals & preferences
    health_goal: str = "general wellness"     # e.g. "weight loss", "muscle gain"
    dietary_restrictions: list[str] = field(default_factory=list)

    # Feed insights from your ai_modules here for richer responses
    active_insights: list[str] = field(default_factory=list)

    def to_context_block(self) -> str:
        """Converts snapshot to a plain-text block injected into the system prompt."""
        lines = [
            f"- Health goal: {self.health_goal}",
            f"- Calories today: {self.calories_today} / {self.calorie_target} kcal",
            f"- Protein: {self.protein_g}g / {self.protein_target_g}g target",
            f"- Carbs: {self.carbs_g}g  |  Fat: {self.fat_g}g",
            f"- Water: {self.water_ml}ml / {self.water_target_ml}ml target",
            f"- Study hours today: {self.study_hours_today}h",
        ]
        if self.focus_score is not None:
            lines.append(f"- Focus score today: {self.focus_score}/10")
        if self.sleep_hours_last_night is not None:
            lines.append(f"- Sleep last night: {self.sleep_hours_last_night}h")
        if self.weekly_adherence_pct is not None:
            lines.append(f"- Weekly goal adherence: {self.weekly_adherence_pct:.0f}%")
        if self.dietary_restrictions:
            lines.append(f"- Dietary restrictions: {', '.join(self.dietary_restrictions)}")
        if self.active_insights:
            lines.append("- Recent AI insights:")
            for insight in self.active_insights:
                lines.append(f"    • {insight}")
        return "\n".join(lines)


# ─────────────────────────────────────────────
# SYSTEM PROMPT
# ─────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are VitaAI, a friendly AI health assistant inside a personal health and wellness tracker app. You help users with:

- Meal suggestions and nutritional advice tailored to their goals and macros
- Study schedule tips and focus optimization strategies
- Sleep, energy, and wellness pattern interpretation
- Motivation and habit coaching

Here is the user's current health data:
{health_context}

Guidelines:
- Always personalize advice using the user's actual data above.
- Keep responses under 150 words unless the user asks for more detail.
- Use a warm, encouraging tone. Never be preachy.
- If asked something outside health/study/wellness, politely redirect.
- Do not diagnose medical conditions or replace professional medical advice.
- Respect dietary restrictions listed above when recommending meals.
"""


# ─────────────────────────────────────────────
# CHATBOT CLASS
# ─────────────────────────────────────────────

class HealthChatbot:
    """
    Stateful per-user chatbot session. One instance per user.

    Example:
        snapshot = UserHealthSnapshot(calories_today=1800, health_goal="muscle gain")
        bot = HealthChatbot(snapshot)
        print(bot.chat("What should I eat for dinner?"))
    """

    def __init__(self, snapshot: UserHealthSnapshot):
        self.snapshot = snapshot
        self.history: list[dict] = []

    def update_snapshot(self, snapshot: UserHealthSnapshot) -> None:
        """Call this after user logs a new meal or activity mid-session."""
        self.snapshot = snapshot

    def chat(self, user_message: str) -> str:
        """Send a message, get a reply. Conversation history is kept automatically."""
        self.history.append({"role": "user", "content": user_message})

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            health_context=self.snapshot.to_context_block()
        )

        response = _client.chat.completions.create(
            model=_model,
            max_tokens=512,
            messages=[
                {"role": "system", "content": system_prompt},
                *self.history,
            ],
        )

        reply = response.choices[0].message.content
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self) -> None:
        """Wipe conversation history. Keeps the snapshot."""
        self.history = []


# ─────────────────────────────────────────────
# FLASK ROUTE
# Copy the block below into your api/routes.py
# ─────────────────────────────────────────────

"""
from flask import request, jsonify
from ai_modules.chatbot import HealthChatbot, UserHealthSnapshot

bot_sessions: dict[str, HealthChatbot] = {}


@app.route("/api/chat", methods=["POST"])
def chat():
    data       = request.get_json()
    user_id    = data.get("user_id")
    message    = data.get("message", "").strip()

    if not user_id or not message:
        return jsonify({"error": "user_id and message are required"}), 400

    # ── Build snapshot from your real DB query ──
    snapshot = UserHealthSnapshot(
        calories_today        = data.get("calories_today", 0),
        calorie_target        = data.get("calorie_target", 2300),
        protein_g             = data.get("protein_g", 0),
        carbs_g               = data.get("carbs_g", 0),
        fat_g                 = data.get("fat_g", 0),
        study_hours_today     = data.get("study_hours_today", 0),
        focus_score           = data.get("focus_score"),
        sleep_hours_last_night= data.get("sleep_hours"),
        health_goal           = data.get("health_goal", "general wellness"),
        dietary_restrictions  = data.get("dietary_restrictions", []),
        active_insights       = data.get("active_insights", []),
    )

    if user_id not in bot_sessions:
        bot_sessions[user_id] = HealthChatbot(snapshot)
    else:
        bot_sessions[user_id].update_snapshot(snapshot)

    reply = bot_sessions[user_id].chat(message)
    return jsonify({"reply": reply, "provider": _provider})


@app.route("/api/chat/reset", methods=["POST"])
def reset_chat():
    user_id = request.get_json().get("user_id")
    if user_id in bot_sessions:
        bot_sessions[user_id].reset()
    return jsonify({"status": "ok"})
"""


# ─────────────────────────────────────────────
# FASTAPI ROUTE
# Use this instead if your project uses FastAPI
# ─────────────────────────────────────────────

"""
from fastapi import FastAPI
from pydantic import BaseModel
from ai_modules.chatbot import HealthChatbot, UserHealthSnapshot

app = FastAPI()
bot_sessions: dict[str, HealthChatbot] = {}


class ChatRequest(BaseModel):
    user_id: str
    message: str
    calories_today: int = 0
    calorie_target: int = 2300
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0
    study_hours_today: float = 0
    focus_score: float | None = None
    sleep_hours: float | None = None
    health_goal: str = "general wellness"
    dietary_restrictions: list[str] = []
    active_insights: list[str] = []


@app.post("/api/chat")
async def chat(req: ChatRequest):
    snapshot = UserHealthSnapshot(
        calories_today         = req.calories_today,
        calorie_target         = req.calorie_target,
        protein_g              = req.protein_g,
        carbs_g                = req.carbs_g,
        fat_g                  = req.fat_g,
        study_hours_today      = req.study_hours_today,
        focus_score            = req.focus_score,
        sleep_hours_last_night = req.sleep_hours,
        health_goal            = req.health_goal,
        dietary_restrictions   = req.dietary_restrictions,
        active_insights        = req.active_insights,
    )
    if req.user_id not in bot_sessions:
        bot_sessions[req.user_id] = HealthChatbot(snapshot)
    else:
        bot_sessions[req.user_id].update_snapshot(snapshot)

    reply = bot_sessions[req.user_id].chat(req.message)
    return {"reply": reply, "provider": _provider}


@app.post("/api/chat/reset")
async def reset_chat(user_id: str):
    if user_id in bot_sessions:
        bot_sessions[user_id].reset()
    return {"status": "ok"}
"""


# ─────────────────────────────────────────────
# QUICK TEST — run: python ai_modules/chatbot.py
# ─────────────────────────────────────────────

if __name__ == "__main__":
    snapshot = UserHealthSnapshot(
        name                   = "Alex",
        calories_today         = 1800,
        calorie_target         = 2300,
        protein_g              = 110,
        protein_target_g       = 150,
        carbs_g                = 220,
        fat_g                  = 55,
        water_ml               = 1200,
        study_hours_today      = 4.5,
        focus_score            = 7.2,
        sleep_hours_last_night = 6.5,
        weekly_adherence_pct   = 72,
        health_goal            = "muscle gain",
        dietary_restrictions   = ["no pork"],
        active_insights        = ["High protein days → +23% next-day focus"],
    )

    bot = HealthChatbot(snapshot)
    print(f"VitaAI ready ({_provider}). Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue
        print(f"\nVitaAI: {bot.chat(user_input)}\n")
