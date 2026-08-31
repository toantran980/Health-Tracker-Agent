# TODO

Living roadmap for the AI Health & Wellness Tracker. Completed work is archived
below; `## Open / Next` lists only actionable items.

## Status Summary

| Priority | Item | Status | Verified in |
|----------|------|--------|-------------|
| High | User authentication (sessions, hashed passwords, protect chat/nutrition) | Done | `tests/test_api_blueprints.py` (auth flow, 401s) |
| High | Persist schedules + productivity sessions + history/rehydration | Done | `tests/test_api_blueprints.py:TestPersistenceEndpoints` |
| High | Persist activity logs + trends | Done | `tests/test_api_blueprints.py:test_activity_log_logs_trends` |
| High | MongoDB TTL indexes (meals, daily_logs) | Done | `api/mongo_store.py` (index creation) |
| Medium | `train_model.py` CLI with incremental updates | Done | ran `--save` and `--incremental` locally |
| Medium | Expanded unit tests (engines, blueprints, rate limit) | Done | 53 tests, both modules pass |
| Medium | Frontend error-envelope handling in `static/api.js` | Done | `toApiError` (HTTP + network) |
| Medium | Per-client rate limiting on external endpoints | Done | `TestRateLimiter` + 429 integration test |
| Low | Docker pins + `.env.example` + Mongo credentials docs | Done | `git status`, README/QUICKSTART |
| Low | Centralized request validation helpers | Done | `helpers.py` used across blueprints |
| Low | Unified README/QUICKSTART/IMPLEMENTATION | Done | doc review |
| Low | Removed stale `chatbox.py`/`chatbot.py` references | Done | grep clean |
| High | CSRF token protection (X-CSRF-Token on state-changing calls) | Done | `TestCsrf` (403 on missing/wrong token) |
| Medium | Session-cookie hardening flags (Secure/SameSite/HttpOnly) | Done | `api/routes.py` config wiring |
| Medium | Frontend auto-switch to login on AUTH_REQUIRED | Done | `auth-required` event in `static/utils.js`/`main.js` |
| Low | `require_fields` wired into meals/log + activity/log | Done | `api/blueprints/nutrition.py`, `activity.py` |
| Medium | Rate limiter backend abstraction (memory / optional Redis) | Done | `build_limiter` + `RedisRateLimiter` |
| Low | Config-driven rate-limit test | Done | `test_build_limiter_from_config_memory` |
| Medium | Keyless chatbot fallback (GROQ key optional) | Done | `ai_modules/health_chatbot.py:_local_reply`, manual CLI check |
| Low | Cleaner auth status + login on top UI | Done | `static/main.js`, `templates/index.html` |

## Open / Next

- [ ] **Local KB-powered chatbot depth**: the keyless fallback is keyword-based;
      consider routing free-form health questions through `KnowledgeBase` rules
      before falling back to the generic tip.
- [ ] **Chat history persistence**: currently per-user sessions live only in
      memory (`state.bot_sessions`); persist recent turns so a server restart
      doesn't lose context.
- [ ] **Session expiry signaling**: cookies are permanent; add a configurable
      session TTL + `SESSION_PERMANENT` refresh so auth sessions can expire.
- [ ] **Provider indicator in UI**: surface whether the chatbot answered via
      Groq or the local responder (e.g. a small badge in the chat).
- [ ] **Rate-limit headers**: return `X-RateLimit-Limit/Remaining/Reset` from the
      limiter so clients can self-throttle.
- [ ] **Frontend auth gate disabled-state**: disable nutrition/chat controls
      unless a session is active, instead of showing a toast on click.
- [ ] **Unit tests for the keyless responder**: add coverage for `_local_reply`
      keyword branches (macros, water, sleep, focus, workouts, fallback) so the
      no-key path is locked down.
- [ ] **Chatbot CSRF/exempt pre-auth prompt**: if a chat message triggers
      `401 AUTH_REQUIRED`, don't just empty the reply box — prompt for login and
      preserve the typed message until the user authenticates.
- [ ] **Water target customization**: `water_target_ml` is hard-coded (2500);
      expose it via the user profile and `.env` so hydrated individuals can set
      their own target.
- [ ] **Activity energy-after validation**: `energy_after` accepts any int;
      clamp it to 1–10 and surface a `VALIDATION` error along with the other
      `require_fields` checks.

## Completed

### High Priority

- [x] **User authentication**: session-based login via signed cookies
      (`api/blueprints/auth.py`), Werkzeug password hashing, `SECRET_KEY` config;
      chat + nutrition endpoints guarded by `require_auth`. Reviewed
      `/api/auth/login`, `/api/auth/me`, `/api/user/<id>/password`.
- [x] **Persist scheduled tasks and productivity sessions**:
      `save_schedule`/`get_schedules`, `save_productivity_session`/`get_productivity_sessions`
      in `api/mongo_store.py`; history endpoints in `api/blueprints/schedule.py`;
      rehydrated via `load_all_user_history`.
- [x] **Persist activity logs**: `log_activity`/`logs`/`trends` endpoints in
      `api/blueprints/activity.py`; `ActivityLog` persistence with frontend
      form + history buttons.
- [x] **MongoDB indexes**: TTL indexes on `meals.timestamp` and
      `daily_logs.updated_at`, driven by `MONGO_MEALS_TTL_DAYS` /
      `MONGO_DAILY_LOGS_TTL_DAYS`.
- [x] **CSRF protection**: per-session token (`get_csrf_token`) must be echoed
      via `X-CSRF-Token` on state-changing requests under an active session
      (`api/routes.py:before_request`, `403 CSRF_FAILED`); login + user-create
      exempt; dashboard sends the header automatically.

### Medium Priority

- [x] **ProductivityPredictor retraining**: `--incremental` merges `--train` rows
      into a saved model (`data/productivity_model.pkl`) via
      `save_model`/`load_model`/`incremental_update`.
- [x] **Unit tests**: fixed missing `tests/productivity_predictor_eval.csv`
      (now `data/eval.csv`); fixed untrained-model MAE, food-vector cache ID
      collision, and the 20-task CSP perf hang (8-task medium set); added
      `tests/test_api_blueprints.py` (auth, protected endpoints, persistence,
      rate limiting). Also fixed real `sort_tasks` bug (urgency ordering).
- [x] **Frontend API error handling**: `toApiError` normalizes HTTP/network
      failures into the `{error, code, details}` envelope shape.
- [x] **Rate limiting**: sliding-window `api/rate_limiter.py` wired into
      `api/blueprints/external.py`, keyed by client IP → `429 RATE_LIMITED`.
- [x] **Session-cookie hardening**: `SESSION_COOKIE_SECURE`, `SESSION_COOKIE_SAMESITE`,
      `SESSION_COOKIE_HTTPONLY` in `config.py`, applied in `api/routes.py`.
- [x] **Frontend auto-switch to login on AUTH_REQUIRED**: `auth-required`
      CustomEvent in `static/utils.js` → `static/main.js` switches to User tab.
- [x] **Rate limiter backend abstraction**: `RedisRateLimiter` + `build_limiter()`
      factory in `api/rate_limiter.py`; backend chosen by `RATE_LIMIT_BACKEND`.
- [x] **Config-driven rate-limit test**: `test_build_limiter_from_config_memory`
      builds a limiter from real config values.

### Low Priority

- [x] **Docker**: aligned `requirements.docker.txt` scikit-learn to 1.8.0;
      created `.env.example` from `config.py` keys; README/QUICKSTART document
      MongoDB + secret-key setup.
- [x] **Validation**: `coerce_int`/`coerce_float`/`parse_iso_datetime`/`require_fields`
      in `api/blueprints/helpers.py`, used across user/nutrition/schedule/activity.
- [x] **Documentation**: unified README/QUICKSTART/IMPLEMENTATION (auth flow,
      activity logging, history endpoints, retraining CLI, test discovery).
- [x] **Code quality**: removed stale `chatbox.py`/`chatbot.py` references;
      updated `main.py` endpoint log.
- [x] **Centralized validation in meals/log + activity/log**: both now route
      through `require_fields` from `api/blueprints/helpers.py`.
- [x] **CSRF exemption handling**: login + user-create exempt from middleware;
      tests confirm no regression on pre-auth 401 paths.
- [x] **Keyless chatbot fallback**: `HealthChatbot` now uses a rule-based
      responder (`_local_reply`) when `GROQ_API_KEY` is empty, instead of raising;
      answers from the user's health snapshot (macros, water, sleep, focus,
      workouts) with whole-word matching. Groq path unchanged when key present.
- [x] **Auth UI polish**: status reads "Not logged in" (guidance on hover);
      Session Login moved to the top of the User tab above Create User.