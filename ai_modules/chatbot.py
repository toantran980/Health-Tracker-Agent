"""
chatbot.py
AI Health Chatbot powered by Anthropic Claude.
Drop this into your existing project and wire it to your Flask/FastAPI routes.

Install:  pip install anthropic
"""

import anthropic
from dataclasses import dataclass, field


# ─────────────────────────────────────────────
# DATA SNAPSHOT  —  feed your real DB values here
# ─────────────────────────────────────────────

@dataclass
class UserHealthSnapshot:
    """
    Populate this from your existing DB/session before calling the chatbot.
    Only the fields you track are needed — missing ones are simply omitted
    from the system prompt.
    """
    name: str = "User"
    calories_today: int = 0
    calorie_target: int = 2300
    protein_g: float = 0
    protein_target_g: float = 150
    carbs_g: float = 0
    fat_g: float = 0
    water_ml: int = 0
    water_target_ml: int = 2500
    study_hours_today: float = 0
    focus_score: float | None = None          # 1–10
    sleep_hours_last_night: float | None = None
    weekly_adherence_pct: float | None = None
    health_goal: str = "general wellness"     # e.g. weight loss, muscle gain
    dietary_restrictions: list[str] = field(default_factory=list)
    active_insights: list[str] = field(default_factory=list)

    def to_context_block(self) -> str:
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
# CHATBOT CLASS
# ─────────────────────────────────────────────

SYSTEM_PROMPT_TEMPLATE = """You are VitaAI, a friendly and knowledgeable AI health assistant embedded in a personal health and wellness tracker app. You help the user with:

• Meal suggestions and nutritional advice tailored to their goals and macros
• Study schedule tips and focus optimization strategies
• Sleep, energy, and wellness pattern interpretation
• Motivation and habit coaching

Here is the user's current health data for today:
{health_context}

Guidelines:
- Always personalize advice using the user's actual data above.
- Be concise — keep responses under 150 words unless the user explicitly asks for more detail.
- Use a warm, encouraging tone. Never be preachy.
- If the user asks something outside health/study/wellness, politely redirect.
- Do not diagnose medical conditions or replace professional medical advice.
- When recommending meals, respect any dietary restrictions listed above.
"""


class HealthChatbot:
    """
    Stateful per-session chatbot. One instance per user conversation.

    Usage:
        snapshot = UserHealthSnapshot(calories_today=1800, ...)
        bot = HealthChatbot(api_key="sk-...", snapshot=snapshot)
        reply = bot.chat("What should I eat for dinner?")
        print(reply)
    """

    def __init__(self, api_key: str, snapshot: UserHealthSnapshot, model: str = "claude-sonnet-4-20250514"):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.snapshot = snapshot
        self.history: list[dict] = []           # grows with each turn

    def update_snapshot(self, snapshot: UserHealthSnapshot) -> None:
        """Call this if user logs a new meal/activity mid-conversation."""
        self.snapshot = snapshot

    def chat(self, user_message: str) -> str:
        """Send a message, get a reply. Conversation history is maintained automatically."""
        self.history.append({"role": "user", "content": user_message})

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            health_context=self.snapshot.to_context_block()
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=system_prompt,
            messages=self.history,
        )

        reply = response.content[0].text
        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self) -> None:
        """Clear history to start a fresh conversation (keep the same snapshot)."""
        self.history = []


# ─────────────────────────────────────────────
# FLASK ROUTE  —  drop into your api/routes.py
# ─────────────────────────────────────────────

"""
Paste the block below into your existing routes.py.
It expects `bot_sessions` (a dict keyed by user_id) to live in your app context,
or replace it with your own session management.

from flask import Flask, request, jsonify, session
from chatbot import HealthChatbot, UserHealthSnapshot
import os

app = Flask(__name__)
app.secret_key = os.environ["FLASK_SECRET"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

bot_sessions: dict[str, HealthChatbot] = {}   # user_id -> HealthChatbot


@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_id = data.get("user_id")
    message = data.get("message", "").strip()

    if not user_id or not message:
        return jsonify({"error": "user_id and message are required"}), 400

    # ── Build snapshot from YOUR existing DB query ──
    # Replace this stub with your real data fetch:
    snapshot = UserHealthSnapshot(
        name=data.get("name", "User"),
        calories_today=data.get("calories_today", 0),
        calorie_target=data.get("calorie_target", 2300),
        protein_g=data.get("protein_g", 0),
        study_hours_today=data.get("study_hours_today", 0),
        focus_score=data.get("focus_score"),
        sleep_hours_last_night=data.get("sleep_hours"),
        health_goal=data.get("health_goal", "general wellness"),
        dietary_restrictions=data.get("dietary_restrictions", []),
    )

    # ── Get or create bot session ──
    if user_id not in bot_sessions:
        bot_sessions[user_id] = HealthChatbot(
            api_key=ANTHROPIC_API_KEY,
            snapshot=snapshot,
        )
    else:
        bot_sessions[user_id].update_snapshot(snapshot)

    reply = bot_sessions[user_id].chat(message)
    return jsonify({"reply": reply})


@app.route("/api/chat/reset", methods=["POST"])
def reset_chat():
    user_id = request.get_json().get("user_id")
    if user_id in bot_sessions:
        bot_sessions[user_id].reset()
    return jsonify({"status": "ok"})
"""


# ─────────────────────────────────────────────
# FASTAPI ROUTE  —  use this instead if you're on FastAPI
# ─────────────────────────────────────────────

"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from chatbot import HealthChatbot, UserHealthSnapshot
import os

app = FastAPI()
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
bot_sessions: dict[str, HealthChatbot] = {}


class ChatRequest(BaseModel):
    user_id: str
    message: str
    calories_today: int = 0
    calorie_target: int = 2300
    protein_g: float = 0
    study_hours_today: float = 0
    focus_score: float | None = None
    sleep_hours: float | None = None
    health_goal: str = "general wellness"
    dietary_restrictions: list[str] = []


@app.post("/api/chat")
async def chat(req: ChatRequest):
    snapshot = UserHealthSnapshot(
        calories_today=req.calories_today,
        calorie_target=req.calorie_target,
        protein_g=req.protein_g,
        study_hours_today=req.study_hours_today,
        focus_score=req.focus_score,
        sleep_hours_last_night=req.sleep_hours,
        health_goal=req.health_goal,
        dietary_restrictions=req.dietary_restrictions,
    )

    if req.user_id not in bot_sessions:
        bot_sessions[req.user_id] = HealthChatbot(
            api_key=ANTHROPIC_API_KEY, snapshot=snapshot
        )
    else:
        bot_sessions[req.user_id].update_snapshot(snapshot)

    reply = bot_sessions[req.user_id].chat(req.message)
    return {"reply": reply}


@app.post("/api/chat/reset")
async def reset_chat(user_id: str):
    if user_id in bot_sessions:
        bot_sessions[user_id].reset()
    return {"status": "ok"}
"""


# ─────────────────────────────────────────────
# QUICK TEST  (run: python chatbot.py)
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import os

    snapshot = UserHealthSnapshot(
        name="Alex",
        calories_today=1800,
        calorie_target=2300,
        protein_g=110,
        protein_target_g=150,
        carbs_g=220,
        fat_g=55,
        water_ml=1200,
        study_hours_today=4.5,
        focus_score=7.2,
        sleep_hours_last_night=6.5,
        weekly_adherence_pct=72,
        health_goal="muscle gain",
        dietary_restrictions=["no pork"],
        active_insights=["High protein days → +23% next-day focus"],
    )

    bot = HealthChatbot(api_key=os.environ["ANTHROPIC_API_KEY"], snapshot=snapshot)

    print("VitaAI chatbot ready. Type 'quit' to exit.\n")
    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue
        reply = bot.chat(user_input)
        print(f"\nVitaAI: {reply}\n")
