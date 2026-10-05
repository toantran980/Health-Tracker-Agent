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
| Medium   | Expanded unit tests (engines, blueprints, rate limit)                    | Done   | 150 tests pass (`pytest`)                                             |
| Medium   | Frontend error-envelope handling in `static/api.js`                     | Done   | `toApiError` (HTTP + network)                                       |
| Medium   | Per-client rate limiting on external endpoints                           | Done   | `TestRateLimiter` + 429 integration test                            |
| Low      | Docker pins +`.env.example` + Mongo credentials docs                   | Done   | `git status`, README/IMPLEMENTATION                               |
| Low      | Centralized request validation helpers                                   | Done   | `helpers.py` used across blueprints                                 |
| Low      | Unified README/IMPLEMENTATION                                           | Done   | doc review                                                            |
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
| High     | Trained productivity model loaded by the API                             | Done   | `TestPretrainedProductivityModel` (`api/blueprints/schedule.py`)     |
| Medium   | Groq free-tier TPM handling (4096 cap, 413 retry)                        | Done   | `TestGroqChatBudget` (`tests/test_ai_modules.py`)                    |
| Medium   | Chat reset auth + history rehydration + non-turn filtering               | Done   | `tests/test_api_blueprints.py`, `tests/test_ai_modules.py`           |
| Medium   | Native HTTP status codes (404/405 passthrough, favicon 204)              | Done   | `TestHTTPErrorHandling`                                              |
| Medium   | Sleep tracking UI (log, history, prediction)                             | Done   | `templates/index.html`, `static/main.js`                             |
| Low      | Frontend layout polish (button rows, grid alignment, hint spacing)       | Done   | `static/styles.css`                                                  |
| Low      | Dead-code cleanup (unused JS exports + CSS palette vars)                 | Done   | repo-wide export/import + CSS selector sweep                         |

## Open / Next

This roadmap assumes a launch target few months - years from now. Revalidate priorities
every few months; do not build a feature only because it appears in the list.

### Urgent next actions (pre-launch priority)

These are the items most likely to affect production readiness and should be treated as the
next critical batch before any public-facing rollout or partner deployment:

- [ ] **Security review** — verify auth, CSRF, session expiry, rate limiting,
  authz boundaries, dependency vulnerabilities, and secret handling in a clean environment.
- [ ] **Reliability testing** — validate restart recovery, MongoDB failure modes,
  external API timeouts, concurrent access, backup/restore, and rollback behavior.
- [ ] **Performance budget** — define target response times and resource budgets for
  core endpoints, recommendation generation, and dashboard loading under realistic traffic.
- [ ] **User acceptance testing** — exercise onboarding, logging, corrections,
  export, deletion, and error-recovery flows with representative users before launch.
- [ ] **Go/no-go review** — record remaining risks, support process, rollback owner,
  and exact release version before public exposure.

These should be completed before investing in deeper product extensions or speculative AI
experiments. Phase 1 and 2 tasks remain useful, but they should not block the launch gate.

### Phase 1: Foundation (before adding more AI)

- [X] **Production deployment baseline** — remove public MongoDB exposure and
  source bind mounts, require external secrets, configure a trusted reverse
  proxy, and verify liveness/readiness probes in a staging environment.
- [X] **Privacy and account controls** — add account deletion, data export, clear
  retention controls, and a documented privacy policy for health data.
- [X] **Data-quality contract** — validate units, timestamps, ranges, time zones,
  duplicate submissions, and missing values consistently across all logs.
- [X] **Observability** — add structured logs, request IDs, error tracking,
  dependency health metrics, and alerts for failed background or external API
  operations.
- [X] **Release process** — add CI linting, dependency/security scanning,
  migration checks, backup-restore drills, staging deployment, and rollback
  instructions.

### Phase 2: Product validation (choose only a few)

- [ ] **Onboarding wizard** — collect goals, fitness level, dietary restrictions,
  schedule, and consent before enabling personalized recommendations.
- [ ] **Export / data portability** — download user history as CSV/JSON with a
  clear date range and explicit handling for failed or partial exports.
- [ ] **MealPlanGenerator / ShoppingList** — produce a weekly plan honoring
  calories, macros, allergies, dietary restrictions, and grocery quantities.
- [X] **Comparative analytics** — add week-over-week trends with explanations,
  confidence indicators, and links back to the underlying logged data.
- [ ] **Wearable data import** — start with one documented CSV/JSON format before
  adding vendor APIs; make imports reviewable and reversible.

### Phase 3: Responsible intelligence

- [X] **External dataset integration** — download the Sleep Health and Lifestyle,
  FitBit, PAMAP2, and UCI Human Activity Recognition datasets into ignored
  `data/external/` folders; document provenance and licenses; add dataset-
  specific preprocessing without merging unrelated targets into
  `training_data.csv`.
- [X] **Train module-specific models** — `models/train_sleep_model.py`,
  `models/train_recovery_model.py`, `models/train_activity_classifier.py`
  produce gitignored `data/*.pkl` from the external datasets with proper
  train/val/test splits; the sleep + recovery predictors load the trained
  models at runtime (falling back to synthetic bootstrap when absent).
- [ ] **Feature store for ML predictors** — share versioned feature engineering
  across productivity, sleep, and recovery models.
- [ ] **Model evaluation and drift checks** — track accuracy by user segment,
  calibration, missing-data behavior, and model versions before deployment.
- [ ] **Explainable recommendations** — show which logged factors influenced a
  recommendation and provide a way to correct inaccurate inputs.
- [X] **Safety boundaries** — label wellness guidance as non-diagnostic, add
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

Every shipped item is listed in the **Status Summary** table above with the test
or file that verifies it, so it is not repeated here. Implementation history is
available in the git log; this file is a roadmap, not a changelog.
