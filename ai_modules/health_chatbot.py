"""
AI Health Chatbot.

Two modes:
  * Groq-powered (recommended, richer answers) when GROQ_API_KEY is set.
    Get a free key at: https://console.groq.com
    Install:  pip install groq   |   .env:  GROQ_API_KEY=gsk_...
  * Keyless rule-based fallback when GROQ_API_KEY is empty or unset.
    Answers questions about the user's macros, water, sleep, focus, and
    workouts from their health snapshot — no network or external dependency.
"""

from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

import config
GROQ_API_KEY = config.GROQ_API_KEY

client   = None
model    = None
provider = None

def init_provider():
    global client, model, provider
    if client is not None:
        return
    if not GROQ_API_KEY:
        # No API key -> keyless rule-based fallback (no network, no dependency).
        provider = "local"
        print("[Chatbot] Provider: local (keyless rule-based — no GROQ_API_KEY set).")
        return
    from groq import Groq
    client   = Groq(api_key=GROQ_API_KEY)
    model    = "openai/gpt-oss-120b"  # Higher intelligence model with reasoning capabilities
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

    def __init__(self, snapshot: UserHealthSnapshot, knowledge_base=None):
        self.snapshot = snapshot
        self.knowledge_base = knowledge_base
        self.history: list[dict] = []

    def update_snapshot(self, snapshot: UserHealthSnapshot) -> None:
        """Adopt a fresh snapshot (live metrics) without losing conversation."""
        self.snapshot = snapshot

    def chat(self, user_message: str) -> str:
        init_provider()
        self.history.append({"role": "user", "content": user_message})
        self.trim_history()

        if provider == "local":
            reply = self.local_reply(user_message)
            self.history.append({"role": "assistant", "content": reply})
            return reply

        try:
            response = client.chat.completions.create(
                model      = model,
                max_completion_tokens = 2048,
                temperature = 1,
                top_p = 1,
                reasoning_effort = "medium",
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

    def local_reply(self, message: str) -> str:
        """
        Keyless fallback responder. Matches keywords against the user's snapshot
        and nutrition targets; answers personal questions directly and degrades
        to general wellness tips for anything else.
        """
        text  = " ".join(message.lower().split())
        s     = self.snapshot
        t     = s.get_targets()

        def has(*words: str) -> bool:
            """True if any whole word (substring OK for multi-word phrases) is present."""
            for w in words:
                if " " in w:
                    if w in text:
                        return True
                elif any(tok == w for tok in text.split()):
                    return True
            return False

        if any(w in text for w in ("water", "hydrat", "drink")):
            progress = s.water_ml / s.water_target_ml * 100
            return (
                f"You've logged {s.water_ml}ml of your {s.water_target_ml}ml target "
                f"({progress:.0f}%). Aim for steady sips throughout the day; "
                f"{max(0, s.water_target_ml - s.water_ml)}ml to go."
            )

        if has("sleep", "rest", "tired", "fatigue"):
            if s.sleep_hours_last_night is not None:
                tgt = 8
                msg = f"You logged {s.sleep_hours_last_night:g}h of sleep last night."
                if s.sleep_hours_last_night < tgt:
                    msg += f" That's {tgt - s.sleep_hours_last_night:.0f}h short of the recommended ~{tgt}h — try a consistent bedtime and limit screens before bed."
                else:
                    msg += " That's a healthy amount — keep it up!"
                return msg
            return "Aim for ~7–9 hours of sleep. Keep a consistent schedule, wind down 30 min before bed, and avoid caffeine after mid-afternoon."

        if has("focus", "productivity", "productive", "study", "concentrate"):
            if s.focus_score is not None:
                return (
                    f"Your recent focus score is {s.focus_score}/10. For an upcoming study block, "
                    f"try a {50 + int(s.focus_score * 5)}-minute deep-work session: one task, phone away, "
                    f"water on hand, then a short break."
                )
            return "For better focus: tackle your hardest task first, work in ~50-minute blocks, and keep your study area distraction-free."

        if has("protein", "muscle", "gym", "gains", "build"):
            return (
                f"Your protein target is {t['protein_g']}g/day ({s.protein_g:.0f}g logged). "
                "Spread it across meals — ~25–30g per meal — and pair it with resistance training for muscle gain."
            )

        if has("exercise", "workout", "activity", "running", "cardio", "walk", "move"):
            return (
                "General advice: mix cardio (3–5x/week) with strength (2–3x/week), "
                "warm up before, hydrate during, and rest at least one day per week. "
                f"Given your {s.health_goal.replace('_',' ')} goal, consistency beats intensity."
            )

        if has("hello", "hi", "hey", "good morning", "good evening", "whats up"):
            return f"Hi {s.name}! Ask me about your macros, water, sleep, focus, or workouts."

        if has("calories", "calorie", "macros", "target", "goal", "how much", "eat", "diet", "meal"):
            return (
                f"Based on your profile ({s.weight_lbs:.0f} lbs, {s.health_goal.replace('_',' ')}):\n"
                f"• Calories: {t['calories']} kcal/day\n"
                f"• Protein:  {t['protein_g']}g\n"
                f"• Carbs:    {t['carbs_g']}g\n"
                f"• Fat:      {t['fat_g']}g\n"
                f"You've logged {s.calories_today} kcal so far ({s.protein_g:.0f}g protein). "
                f"{'Getting closer to your target.' if s.calories_today <= t['calories'] else 'A bit over today — consider a lighter dinner.'}"
            )

        # Free-form health/goal questions: route through the rule-based KB
        # before degrading to a generic tip.
        kb_reply = self.kb_reply()
        if kb_reply:
            return kb_reply

        return (
            "Here's a general wellness tip: build your plate around lean protein, "
            "vegetables, and whole grains, drink water consistently, get 7–9h of sleep, "
            "and move daily. I'm running in keyless mode, so for deeper answers add a "
            "GROQ_API_KEY to your .env — otherwise I can answer about your macros, "
            "water, sleep, focus, or workouts."
        )

    def kb_reply(self) -> Optional[str]:
        """
        Ask the per-user KnowledgeBase for a recommendation drawn from the live
        snapshot facts. Returns a formatted suggestion, or None if no rule fires
        (in which case the caller falls back to a generic tip).
        """
        if not self.knowledge_base:
            return None
        s = self.snapshot
        try:
            self.knowledge_base.add_facts({
                "daily_calories":          s.calories_today,
                "daily_protein":           s.protein_g,
                "energy_level":            s.focus_score if s.focus_score is not None else 5,
                "sleep_hours":             s.sleep_hours_last_night if s.sleep_hours_last_night is not None else 0,
                "upcoming_difficulty":     5,
                "recent_session_duration": s.study_hours_today * 60,
                "macro_balance":           "balanced",
                "macro_balance_details":   {},
                "correlation_nutrition_study": 0.0,
                "adherence_rate":          (s.weekly_adherence_pct or 0) / 100.0,
            })
            recs = self.knowledge_base.get_top_recommendations(n=1)
            self.knowledge_base.clear_facts()
            if not recs:
                return None
            rec = recs[0]
            suggestion = rec.get("suggestion", "")
            explanation = self.knowledge_base.explain_recommendation(rec)
            return f"{suggestion}\n({explanation})".strip()
        except Exception:
            return None




    def reset(self) -> None:
        """Clear conversation history, keep snapshot."""
        self.history = []

    def set_history(self, messages: list[dict]) -> None:
        """Restore a previously persisted conversation (must be role/content dicts)."""
        clean = [
            {"role": m.get("role"), "content": m.get("content")}
            for m in messages
            if m.get("role") in ("user", "assistant") and m.get("content")
        ]
        self.history = clean[- (MAX_HISTORY_PAIRS * 2):]

    def get_provider(self) -> str:
        return provider or "none"

    def trim_history(self) -> None:
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