# Spark Ideas — AI Modules & Features

Brainstorm of potential new AI modules and features for the Health & Wellness
Tracker. Items are intentionally unordered and are not commitments. Before
promoting an idea into `TODO.md`, check that it has a clear user problem, a
reliable data source, a measurable success metric, an acceptable privacy cost,
and a realistic maintenance plan.

<!-- Previous batch promoted to TODO.md → Open / Next on 2026-09-02 -->

## Promotion checklist

Move an idea to `TODO.md` only when:

- [ ] the target user and problem are specific;
- [ ] required data, permissions, and external services are identified;
- [ ] a small first version can be tested without building the whole system;
- [ ] health-safety, privacy, and abuse risks have an owner;
- [ ] success and failure can be measured; and
- [ ] the operational cost is acceptable for the planned launch stage.

Ideas that need new data, medical interpretation, social features, or ongoing
background jobs should remain here until the foundation work in `TODO.md` is
complete.

---

## AI Modules (new engine candidates)

- **BodyCompositionEstimator** — infer lean mass / body-fat % trends from
  weight, calorie surplus/deficit, and workout volume over time; feed into
  `MealRecommendationEngine` macro targets.
- **InjuryRiskPredictor** — flag overtraining signals (rapid volume spikes,
  low sleep + high intensity combos) and suggest deload weeks before injury
  occurs.
- **CircadianRhythmOptimizer** — recommend optimal workout, meal, and sleep
  windows based on chronotype (morningness score) and logged energy levels
  throughout the day.
- **CravingPredictor** — correlate logged mood, sleep deficit, and
  macronutrient gaps with self-reported cravings; proactively suggest
  satisfying, on-plan snacks before cravings strike.
- **NutrientDeficiencyDetector** — scan multi-day micro-nutrient logs for
  consistent shortfalls (iron, vitamin D, magnesium, etc.) and surface
  food-first remediation suggestions before supplement recommendations.
- **AdaptiveWorkoutIntensityEngine** — auto-scale suggested workout intensity
  for the day using `RecoveryPredictor` output + rolling 7-day HRV proxy
  (derived from logged resting heart rate).
- **SymptomCorrelationAnalyzer** — let users tag daily symptoms (headache,
  bloating, fatigue) and ML-surface dietary or sleep patterns that precede them
  with high correlation over a rolling window.
- **PersonalizedSupplementAdvisor** — rule-based (not medical advice)
  engine that maps detected nutrient gaps + goals (muscle gain, endurance,
  cognition) to evidence-backed supplement options with dosage ranges.

---

## Feature / UX ideas

- **Voice-input food logging** — browser `SpeechRecognition` API to dictate
  meals ("I had a banana and two eggs") parsed by the chatbot into structured
  nutrition log entries.
- **Photo-based meal recognition** — upload a meal photo → call a vision
  API (e.g., Google Vision or a lightweight CLIP model) to infer likely foods
  and pre-fill the nutrition log form.
- **Friend / social challenges** — opt-in social layer: share a weekly step
  count or calorie streak with a friend code; leaderboard with privacy controls.
- **Habit stacking builder** — UI wizard that chains existing user habits
  (morning coffee → 10 min stretch → log weight) into an ordered routine card
  shown at the right time of day.
- **In-app coach messages** — proactive push-style toasts (not emails) at
  user-configured times: "You haven't logged water in 3 hours" or "Great week —
  you hit protein 6/7 days."
- **Wearable data import** — CSV/JSON ingest from Fitbit, Garmin export, or
  Apple Health; map steps, HRV, and sleep stages into existing activity/sleep
  logs.
- **Comparative analytics dashboard** — side-by-side week-over-week charts
  (calories, sleep, steps, mood score) with automated delta annotations.
- **Printable / shareable report** — one-click PDF of the weekly digest for
  sharing with a coach, dietitian, or doctor; generated server-side with
  `reportlab` or client-side with `jsPDF`.
- **Onboarding wizard** — multi-step first-run flow collecting goal, fitness
  level, dietary restrictions, and chronotype to pre-configure defaults
  (water target, macro split, schedule preferences).
- **Dark / light / system theme toggle** — CSS custom-property theming with
  a `prefers-color-scheme` default and manual override persisted in
  `localStorage`.

---

## Cross-cutting / Engineering

- **WebSocket real-time updates** — push nutrition/activity log changes to
  other open tabs instantly using Flask-SocketIO instead of polling; useful for
  future multi-device scenarios.
- **Progressive Web App (PWA) support** — add `manifest.json` + service
  worker for offline caching of the dashboard shell and queued log submissions
  when connectivity returns.
- **FHIR-compatible data export** — structure exported health data as FHIR
  R4 `Observation` resources so it can be imported into EHR systems or shared
  with clinicians.
- **End-to-end field encryption** — encrypt sensitive `daily_logs` / chat
  fields at rest using a per-user key derived from the password hash, so even a
  DB breach leaks no plaintext health data.
- **Event sourcing for audit trail** — store every mutation as an immutable
  event (append-only `events` collection in Mongo) alongside the current-state
  collections; enables full history replay and undo.
- **GraphQL API gateway** — thin GraphQL layer over existing REST blueprints
  so a future mobile client can request exactly the fields it needs without
  over-fetching.
- **Async task queue (Celery + Redis)** — offload heavy ML inference,
  weekly digest generation, and external API fan-out to a Celery worker pool
  rather than blocking Flask request threads.
- **Observability stack** — structured JSON logging (already partial) wired
  into an OpenTelemetry collector; export traces/metrics to Jaeger / Prometheus
  for production debugging.
- **Multi-user admin panel** — super-admin view to inspect active users,
  rate-limit overrides, and manually trigger model retraining for a specific
  user cohort.
