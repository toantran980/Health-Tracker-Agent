# Spark Ideas — AI Modules & Features

Brainstorm of potential new AI modules and features for the Health & Wellness
Tracker. Items are unordered ideas, not committed roadmap items — move anything
you decide to build into `TODO.md`'s Open/Next section.

## AI Modules (new engine candidates)

- **Stress / RecoveryPredictor** — predict readiness/recovery from sleep,
  workout load, and self-reported stress. Distinct from `ProductivityPredictor`
  (which targets focus/study). Could feed the scheduler to avoid over-training
  on low-readiness days.
- **ExercisePlanGenerator** — build a personalized weekly workout plan from
  goal, fitness level, and available days (currently activity recs are one-off
  suggestions, not a structured plan).
- **HydrationTrackerEngine** — schedule/remind water intake based on weight,
  activity level, and weather (currently water is a static daily counter).
- **SleepQualityPredictor** — ML to predict sleep quality from bedtime,
  caffeine, screen time, and exercise; complements productivity forecasting.
- **MealPlanGenerator / ShoppingList** — extend `MealRecommendationEngine` from
  single-meal suggestions to a full weekly plan plus a grocery list, honoring
  macros and dietary restrictions.
- **MoodAnalyzer** — light sentiment/emotion analysis over journal or chatbot
  entries to surface mood trends over time.
- **HealthRiskAssessor** — flag logged values outside healthy ranges (BMI,
  micronutrients, calorie deviations) with rule-based warnings.

## Feature / UX ideas

- **Automated weekly digest** — summarize adherence, trends, and next-week
  recommendations.
- **Streaks & gamification** — streak counters, badges, and gentle nudges to
  reinforce habits.
- **Export / data portability** — download user history as CSV/JSON.
- **Goal milestone tracking** — progress bars toward weight/muscle targets with
  projected completion dates.
- **Weather-aware recommendations** — fold weather into outdoor activity and
  hydration suggestions.

## Cross-cutting / engineering

- **Prompt-versioned chatbot** — keep a changelog of the Groq system prompt and
  the rule-based responder.
- **Feature store for the ML predictors** — cache engineered features so models
  share a consistent input pipeline.
- **A/B flag for recommendation engines** — compare rule vs. ML outputs
  before/after switchover.
