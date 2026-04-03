"""
chatbot.py

AI Health Chatbot — uses OpenAI (gpt-4o-mini) as primary LLM.
Falls back to Groq (llama-3.3-70b-versatile, free tier) if no OpenAI key.
Both providers use the same interface so the rest of the app is unaffected.

Install:  pip install openai groq python-dotenv

Setup (.env):
    OPENAI_API_KEY=sk-...       # takes priority if both keys present
    GROQ_API_KEY=gsk_...        # free at https://console.groq.com
"""

import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

#OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY",   "")

# Lazy provider init: fails at chat() time, not at import time
# This prevents a missing .env key from crashing the entire Flask app on
# startup.  The error is surfaced only when a user actually tries to chat.
client   = None
model    = None
provider = None

def _init_provider():
    """Initialise the LLM client on first use."""
    global client, model, provider

    if client is not None:
        return   # already initialised

    '''if OPENAI_API_KEY:
        from openai import OpenAI
        client   = OpenAI(api_key=OPENAI_API_KEY)
        model    = "gpt-5"
        provider = "openai"'''
    if GROQ_API_KEY:
        from groq import Groq
        client   = Groq(api_key=GROQ_API_KEY)
        model    = "llama-3.3-70b-versatile"
        provider = "groq"
    else:
        raise EnvironmentError(
            "No AI key found. Add OPENAI_API_KEY or GROQ_API_KEY to your .env file.\n"
            "Get a free Groq key at: https://console.groq.com"
        )

    print(f"[Chatbot] Provider: {provider}  |  Model: {model}")


# ── Conversation window limit ─────────────────────────────────────────────
# Keep only the last N user+assistant message pairs so history never grows
# large enough to hit the model's context-window limit.
MAX_HISTORY_PAIRS = 20


# ═══════════════════════════════════════════════════════════════════════════
# USER HEALTH SNAPSHOT
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class UserHealthSnapshot:
    """
    Current health state injected into the chatbot system prompt.

    Pass real values from your database — only fields you track are needed.
    None / missing fields are omitted from the AI context automatically.
    """
    name: str = "User"

    # ── Diet ─────────────────────────────────────────────────────────────
    calories_today:    int   = 0
    calorie_target:    int   = 2300
    protein_g:         float = 0.0
    protein_target_g:  float = 150.0
    carbs_g:           float = 0.0
    fat_g:             float = 0.0
    water_ml:          int   = 0
    water_target_ml:   int   = 2500

    # ── Study & focus ─────────────────────────────────────────────────────
    study_hours_today:      float          = 0.0
    focus_score:            Optional[float] = None   # 1-10 scale

    # ── Wellness ──────────────────────────────────────────────────────────
    sleep_hours_last_night: Optional[float] = None
    weekly_adherence_pct:   Optional[float] = None

    # ── Goals & preferences ───────────────────────────────────────────────
    health_goal:          str        = "general wellness"
    dietary_restrictions: list[str]  = field(default_factory=list)

    # ── Feed insights from NutritionAnalyzer / KnowledgeBase here ─────────
    active_insights: list[str] = field(default_factory=list)

    def to_context_block(self) -> str:
        """
        Render snapshot as a plain-text block for the system prompt.
        Only includes lines where data is actually present.
        """
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


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════

_SYSTEM_PROMPT_TEMPLATE = """You are VitaAI, a friendly AI health assistant inside a personal health and wellness tracker app.

You help users with:
- Meal suggestions and nutritional advice tailored to their goals and macros
- Study schedule tips and focus optimisation strategies
- Sleep, energy, and wellness pattern interpretation
- Motivation and habit coaching

Here is the user's current health data:
{health_context}

Guidelines:
- Always personalise advice using the user's actual data above.
- Keep responses under 150 words unless the user explicitly asks for more detail.
- Use a warm, encouraging tone. Never be preachy or repetitive.
- If asked something outside health, study, or wellness, politely redirect.
- Do not diagnose medical conditions or replace professional medical advice.
- Always respect any dietary restrictions listed above when recommending food.
"""


# ═══════════════════════════════════════════════════════════════════════════
# CHATBOT CLASS
# ═══════════════════════════════════════════════════════════════════════════

class HealthChatbot:
    """
    Stateful per-user chatbot session.

    One instance per user, stored in bot_sessions dict in routes.py.
    Conversation history is kept as a rolling window of MAX_HISTORY_PAIRS
    message pairs to prevent context-window overflow on long sessions.

    Example:
        snapshot = UserHealthSnapshot(calories_today=1800, health_goal="muscle gain")
        bot      = HealthChatbot(snapshot)
        print(bot.chat("What should I eat for dinner?"))
    """

    def __init__(self, snapshot: UserHealthSnapshot):
        self.snapshot = snapshot
        self.history: list[dict] = []

    def update_snapshot(self, snapshot: UserHealthSnapshot) -> None:
        """
        Replace the health snapshot mid-session.
        Call this after the user logs a new meal or activity so the next
        chatbot response reflects up-to-date data.
        """
        self.snapshot = snapshot

    def chat(self, user_message: str) -> str:
        """
        Send a message and get a reply.

        Conversation history is maintained automatically as a rolling window.
        Raises EnvironmentError if no API key is configured.
        Returns an error string (not a raise) on API failures so the Flask
        route always returns a valid JSON response.
        """
        _init_provider()   # lazy init — raises EnvironmentError if no key

        self.history.append({"role": "user", "content": user_message})
        self._trim_history()

        system_prompt = _SYSTEM_PROMPT_TEMPLATE.format(
            health_context=self.snapshot.to_context_block()
        )

        try:
            response = client.chat.completions.create(
                model      = model,
                max_tokens = 512,
                messages   = [
                    {"role": "system", "content": system_prompt},
                    *self.history,
                ],
            )
            reply = response.choices[0].message.content.strip()

        except Exception as e:
            # Remove the user message we just appended so history stays clean
            self.history.pop()
            print(f"[Chatbot] API error ({provider}): {e}")
            reply = (
                "I'm having trouble connecting right now. "
                "Please try again in a moment."
            )

        self.history.append({"role": "assistant", "content": reply})
        return reply

    def reset(self) -> None:
        """Wipe conversation history. Keeps the current snapshot."""
        self.history = []

    def get_provider(self) -> str:
        """Return the active LLM provider name, or 'none' if not yet initialised."""
        return provider or "none"

    # ── Private ────────────────────────────────────────────────────────
    def _trim_history(self) -> None:
        """
        Keep only the last MAX_HISTORY_PAIRS user/assistant pairs.

        Without trimming, a long conversation eventually exceeds the model's
        context window and raises an API error.
        """
        max_messages = MAX_HISTORY_PAIRS * 2   # each pair = 2 messages
        if len(self.history) > max_messages:
            self.history = self.history[-max_messages:]


# ═══════════════════════════════════════════════════════════════════════════
# QUICK TEST — run: python ai_modules/chatbot.py
# ═══════════════════════════════════════════════════════════════════════════

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
        active_insights        = ["High protein days correlate with +23% next-day focus"],
    )

    bot = HealthChatbot(snapshot)
    print(f"VitaAI ready ({bot.get_provider()}). Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break
        if not user_input:
            continue
        print(f"\nVitaAI: {bot.chat(user_input)}\n")