# TODO

Living roadmap for the AI Health & Wellness Tracker. Completed work is archived
below; `## Open / Next` lists only actionable items.

## Status Summary

| Priority | Item                                                                     | Status | Verified in                                                           |
| -------- | ------------------------------------------------------------------------ | ------ | --------------------------------------------------------------------- |
| High     | User authentication (sessions, hashed passwords, protect chat/nutrition) | Done   | `tests/test_api_blueprints.py` (auth flow, 401s)                    |
| High     | Persist schedules + productivity sessions + history/rehydration          | Done   | `tests/test_api_blueprints.py:TestPersistenceEndpoints`             |
| High     | Persist activity logs + trends                                           | Done   | `tests/test_api_blueprints.py:test_activity_log_logs_trends`        |
| High     | MongoDB TTL indexes (meals, daily_logs)                                  | Done   | `api/mongo_store.py` (index creation)                               |
| Medium   | `train_model.py` CLI with incremental updates                          | Done   | ran`--save` and `--incremental` locally                           |
| Medium   | Expanded unit tests (engines, blueprints, rate limit)                    | Done   | 53 tests, both modules pass                                           |
| Medium   | Frontend error-envelope handling in`static/api.js`                     | Done   | `toApiError` (HTTP + network)                                       |
| Medium   | Per-client rate limiting on external endpoints                           | Done   | `TestRateLimiter` + 429 integration test                            |
| Low      | Docker pins +`.env.example` + Mongo credentials docs                   | Done   | `git status`, README/QUICKSTART                                     |
| Low      | Centralized request validation helpers                                   | Done   | `helpers.py` used across blueprints                                 |
| Low      | Unified README/QUICKSTART/IMPLEMENTATION                                 | Done   | doc review                                                            |
| Low      | Removed stale`chatbox.py`/`chatbot.py` references                    | Done   | grep clean                                                            |
| High     | CSRF token protection (X-CSRF-Token on state-changing calls)             | Done   | `TestCsrf` (403 on missing/wrong token)                             |
| Medium   | Session-cookie hardening flags (Secure/SameSite/HttpOnly)                | Done   | `api/routes.py` config wiring                                       |
| Medium   | Frontend auto-switch to login on AUTH_REQUIRED                           | Done   | `auth-required` event in `static/utils.js`/`main.js`            |
| Low      | `require_fields` wired into meals/log + activity/log                   | Done   | `api/blueprints/nutrition.py`, `activity.py`                      |
| Medium   | Rate limiter backend abstraction (memory / optional Redis)               | Done   | `build_limiter` + `RedisRateLimiter`                              |
| Low      | Config-driven rate-limit test                                            | Done   | `test_build_limiter_from_config_memory`                             |
| Medium   | Keyless chatbot fallback (GROQ key optional)                             | Done   | `ai_modules/health_chatbot.py:_local_reply`, manual CLI check       |
| Low      | Cleaner auth status + login on top UI                                    | Done   | `static/main.js`, `templates/index.html`                          |
| High     | Keyless responder unit tests                                             | Done   | `tests/test_ai_modules.py:TestKeylessChatbotFallback` (11 tests)    |
| Medium   | Chat provider indicator (Groq/local badge)                               | Done   | `api/blueprints/chat.py`, `static/ui.js`                          |
| Medium   | Rate-limit response headers                                              | Done   | `api/rate_limiter.py:status`, `api/blueprints/external.py` + test |
| Medium   | Water target customization                                               | Done   | `models/user_profile.py`, `api/blueprints/user.py`, form + tests  |
| Medium   | Activity`energy_after` validation                                      | Done   | `coerce_int` min/max in `activity.py` + test                      |
| Medium   | Frontend auth gate disabled-state                                        | Done   | `setAuthGate` in `static/main.js`                                 |
| Medium   | Chatbot pre-auth prompt (keep message, prompt login)                     | Done   | `static/main.js` chat handler + `ui.js`                           |
| Medium   | Session expiry signaling + sliding refresh                               | Done   | `config.py`, `api/routes.py`, `TestSessionExpiry`               |
| Medium   | Chat history persistence                                                 | Done   | `api/mongo_store.py` + `chat.py` rehydration                      |
| Medium   | Local KB-powered chatbot depth                                           | Done   | `kb_reply()` in `ai_modules/health_chatbot.py`                    |
| High     | HealthRiskAssessor (rule-based risk & anomaly warnings)                  | Done   | `tests/test_new_modules.py:TestHealthRiskAssessor`                  |
| High     | SleepQualityPredictor (RF ML model + hygiene advice)                     | Done   | `tests/test_new_modules.py:TestSleepQualityPredictor`               |
| High     | Stress / RecoveryPredictor (RF physical readiness ML)                    | Done   | `tests/test_new_modules.py:TestRecoveryPredictor`                   |
| High     | Goal milestone tracking (weight, exercise, nutrition)                    | Done   | `tests/test_new_modules.py:TestGoalTracker`                         |
| High     | Automated weekly digest (multi-domain report)                            | Done   | `tests/test_new_modules.py:TestWeeklyDigestGenerator`               |

## Open / Next

This roadmap assumes a launch target few months - years from now. Revalidate priorities
every few months; do not build a feature only because it appears in the list.

### Phase 1: Foundation (before adding more AI)

- [ ] **Production deployment baseline** — remove public MongoDB exposure and
  source bind mounts, require external secrets, configure a trusted reverse
  proxy, and verify liveness/readiness probes in a staging environment.
- [ ] **Privacy and account controls** — add account deletion, data export, clear
  retention controls, and a documented privacy policy for health data.
- [ ] **Data-quality contract** — validate units, timestamps, ranges, time zones,
  duplicate submissions, and missing values consistently across all logs.
- [ ] **Observability** — add structured logs, request IDs, error tracking,
  dependency health metrics, and alerts for failed background or external API
  operations.
- [ ] **Release process** — add CI linting, dependency/security scanning,
  migration checks, backup-restore drills, staging deployment, and rollback
  instructions.

### Phase 2: Product validation (choose only a few)

- [ ] **Onboarding wizard** — collect goals, fitness level, dietary restrictions,
  schedule, and consent before enabling personalized recommendations.
- [ ] **Export / data portability** — download user history as CSV/JSON with a
  clear date range and explicit handling for failed or partial exports.
- [ ] **MealPlanGenerator / ShoppingList** — produce a weekly plan honoring
  calories, macros, allergies, dietary restrictions, and grocery quantities.
- [ ] **Comparative analytics** — add week-over-week trends with explanations,
  confidence indicators, and links back to the underlying logged data.
- [ ] **Wearable data import** — start with one documented CSV/JSON format before
  adding vendor APIs; make imports reviewable and reversible.

### Phase 3: Responsible intelligence

- [ ] **Feature store for ML predictors** — share versioned feature engineering
  across productivity, sleep, and recovery models.
- [ ] **Model evaluation and drift checks** — track accuracy by user segment,
  calibration, missing-data behavior, and model versions before deployment.
- [ ] **Explainable recommendations** — show which logged factors influenced a
  recommendation and provide a way to correct inaccurate inputs.
- [ ] **Safety boundaries** — label wellness guidance as non-diagnostic, add
  escalation language for concerning symptoms, and review high-risk rules
  with a qualified professional.
- [ ] **Prompt-versioned chatbot** — version prompts and local fallback behavior,
  redact sensitive logs, and add regression tests for unsafe or misleading
  responses.

### Phase 4: Launch gate (complete before public release)

- [ ] **Security review** — verify authentication, CSRF, session expiry, rate
  limits, authorization boundaries, dependency vulnerabilities, and secret
  handling in a clean environment.
- [ ] **Reliability testing** — test restart recovery, MongoDB failure, external
  API timeouts, concurrent users, backups, and restore procedures.
- [ ] **Performance budget** — establish response-time and resource limits for
  core endpoints, recommendation generation, and dashboard loads.
- [ ] **User acceptance testing** — test onboarding, logging, corrections,
  export, deletion, and error recovery with representative users.
- [ ] **Go/no-go review** — record open risks, known limitations, rollback owner,
  support process, and the exact release version.

### Deferred experiments

- [ ] **HydrationTrackerEngine**, **ExercisePlanGenerator**, and **MoodAnalyzer**
  — build only after the underlying data and safety boundaries are ready.
- [ ] **Streaks and gamification** — consider after retention is measured; avoid
  incentives that encourage unhealthy logging or exercise behavior.
- [ ] **Voice/photo logging**, **social challenges**, **PWA**, **WebSockets**,
  **GraphQL**, and **Celery** — keep in `SPARK_IDEAS.md` until a validated
  user problem justifies their operational cost.

## Completed

### High Priority

- [X] **User authentication**: session-based login via signed cookies
  (`api/blueprints/auth.py`), Werkzeug password hashing, `SECRET_KEY` config;
  chat + nutrition endpoints guarded by `require_auth`. Reviewed
  `/api/auth/login`, `/api/auth/me`, `/api/user/<id>/password`.
- [X] **Persist scheduled tasks and productivity sessions**:
  `save_schedule`/`get_schedules`, `save_productivity_session`/`get_productivity_sessions`
  in `api/mongo_store.py`; history endpoints in `api/blueprints/schedule.py`;
  rehydrated via `load_all_user_history`.
- [X] **Persist activity logs**: `log_activity`/`logs`/`trends` endpoints in
  `api/blueprints/activity.py`; `ActivityLog` persistence with frontend
  form + history buttons.
- [X] **MongoDB indexes**: TTL indexes on `meals.timestamp` and
  `daily_logs.updated_at`, driven by `MONGO_MEALS_TTL_DAYS` /
  `MONGO_DAILY_LOGS_TTL_DAYS`.
- [X] **CSRF protection**: per-session token (`get_csrf_token`) must be echoed
  via `X-CSRF-Token` on state-changing requests under an active session
  (`api/routes.py:before_request`, `403 CSRF_FAILED`); login + user-create
  exempt; dashboard sends the header automatically.

### Medium Priority

- [X] **ProductivityPredictor retraining**: `--incremental` merges `--train` rows
  into a saved model (`data/productivity_model.pkl`) via
  `save_model`/`load_model`/`incremental_update`.
- [X] **Unit tests**: fixed missing `tests/productivity_predictor_eval.csv`
  (now `data/eval.csv`); fixed untrained-model MAE, food-vector cache ID
  collision, and the 20-task CSP perf hang (8-task medium set); added
  `tests/test_api_blueprints.py` (auth, protected endpoints, persistence,
  rate limiting). Also fixed real `sort_tasks` bug (urgency ordering).
- [X] **Frontend API error handling**: `toApiError` normalizes HTTP/network
  failures into the `{error, code, details}` envelope shape.
- [X] **Rate limiting**: sliding-window `api/rate_limiter.py` wired into
  `api/blueprints/external.py`, keyed by client IP → `429 RATE_LIMITED`.
- [X] **Session-cookie hardening**: `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`,
  `SESSION_COOKIE_HTTPONLY` in `config.py`, applied in `api/routes.py`.
- [X] **Frontend auto-switch to login on AUTH_REQUIRED**: `auth-required`
  CustomEvent in `static/utils.js` → `static/main.js` switches to User tab.
- [X] **Rate limiter backend abstraction**: `RedisRateLimiter` + `build_limiter()`
  factory in `api/rate_limiter.py`; backend chosen by `RATE_LIMIT_BACKEND`.
- [X] **Config-driven rate-limit test**: `test_build_limiter_from_config_memory`
  builds a limiter from real config values.

### Low Priority

- [X] **Docker**: aligned `requirements.docker.txt` scikit-learn to 1.8.0;
  created `.env.example` from `config.py` keys; README/QUICKSTART document
  MongoDB + secret-key setup.
- [X] **Validation**: `coerce_int`/`coerce_float`/`parse_iso_datetime`/`require_fields`
  in `api/blueprints/helpers.py`, used across user/nutrition/schedule/activity.
- [X] **Documentation**: unified README/QUICKSTART/IMPLEMENTATION (auth flow,
  activity logging, history endpoints, retraining CLI, test discovery).
- [X] **Code quality**: removed stale `chatbox.py`/`chatbot.py` references;
  updated `main.py` endpoint log.
- [X] **Centralized validation in meals/log + activity/log**: both now route
  through `require_fields` from `api/blueprints/helpers.py`.
- [X] **CSRF exemption handling**: login + user-create exempt from middleware;
  tests confirm no regression on pre-auth 401 paths.
- [X] **Keyless chatbot fallback**: `HealthChatbot` now uses a rule-based
  responder (`_local_reply`) when `GROQ_API_KEY` is empty, instead of raising;
  answers from the user's health snapshot (macros, water, sleep, focus,
  workouts) with whole-word matching. Groq path unchanged when key present.
- [X] **Auth UI polish**: status reads "Not logged in" (guidance on hover);
  Session Login moved to the top of the User tab above Create User.

### Recently Completed

- [X] **Keyless responder unit tests**: `TestKeylessChatbotFallback` covers each
  `_local_reply` branch (macros, water, sleep, focus, protein, greeting,
  generic fallback, substring false-positive) and history preservation.
- [X] **Provider indicator in UI**: `/api/chat` now returns `provider`
  (`groq`/`local`); the assistant chat bubble shows an LLM/Local badge
  (with hover tooltip).
- [X] **Rate-limit headers**: `RateLimiter.status()` exposes
  `limit/remaining/reset`; external endpoints stamp `X-RateLimit-Limit/ Remaining/Reset` on both success and 429 responses (added
  `test_rate_limit_headers_present_on_success_and_429`).
- [X] **Water target customization**: `water_target_ml` is now a configurable
  `UserProfile` field (default 2500), accepted/validated on `/api/user/create`
  (`coerce_int` 0–10000), round-trips through Mongo (`user_from_doc`), and is
  passed to the chatbot snapshot. Frontend `config.js`/`main.js`/`index.html`
  add a Water (mL/day) field. Covered by `TestAuthFlow`.
- [X] **Activity `energy_after` validation**: `/api/activity/log` rejects
  out-of-range values via `coerce_int(minimum=1, maximum=10)` with a
  `VALUE_OUT_OF_RANGE` 400 error. Covered by
  `test_activity_energy_after_out_of_range_rejected`.
- [X] **Frontend auth gate disabled-state**: `setAuthGate(authenticated)` in
  `static/main.js` disables the nutrition/chat/schedule/form controls until a
  session is active; toggled from `updateAuthStatus()` and the `auth-required`
  handler (instead of only showing a toast on click).
- [X] **Chatbot pre-auth prompt**: on `AUTH_REQUIRED` during chat, the just-appended
  user bubble is removed (`removeLastChatMessage` in `static/ui.js`) and the
  typed message is preserved in the input while the UI prompts for login.
- [X] **Session expiry signaling**: `SESSION_LIFETIME_MINUTES` (default 0 =
  permanent) + `SESSION_REFRESH` sliding TTL via `PERMANENT_SESSION_LIFETIME`
  and `session.permanent` in `api/routes.py:apply_session_expiry`; documented in
  `.env.example`; covered by `TestSessionExpiry`.
- [X] **Chat history persistence**: `MongoStore.save_chat_history` /
  `get_chat_history` / `delete_chat_history` (unique `chat_history` index);
  `api/blueprints/chat.py` saves turns after each message and rehydrates the bot
  via `HealthChatbot.set_history` on restart; reset wipes stored history.
- [X] **Local KB-powered chatbot depth**: `HealthChatbot.kb_reply()` routes free-form
  health questions through the per-user `KnowledgeBase` (facts derived from the
  live snapshot) before falling back to the generic tip; the blueprint wires in
  `state.knowledge_bases[user_id]`.
- [X] **CSRF session key rename**: `_csrf_token` session key renamed to `csrf_token`
  (`api/routes.py`, `api/blueprints/helpers.py`) — no underscore prefix.
