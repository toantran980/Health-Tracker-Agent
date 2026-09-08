# Health Data Privacy Policy

**Effective Date:** September 2026  
**Version:** 1.0.0

The AI Health & Wellness Tracker collects, processes, and persists health-related information to generate personalized wellness recommendations, nutritional analyses, and productivity schedules. This document outlines our data practices, security protections, and your privacy rights under GDPR, CCPA, and general health-data stewardship standards.

---

## 1. Information We Collect

We collect only information voluntarily provided by the user or computed to support wellness tracking:

1. **User Profile Data**:
   - Age, current weight (kg), height (cm), biological sex, health and fitness goals.
   - Credentials: password hash (one-way hashed using Werkzeug `scrypt`/`pbkdf2:sha256`; plaintext passwords are never stored or logged).

2. **Nutritional Logs**:
   - Meals logged, food items, calorie counts, macronutrient breakdowns (protein, carbs, fat), water intake, and timestamps.

3. **Physical Activity Logs**:
   - Activity types (exercise, study, rest, work), duration in minutes, post-activity energy scores (1-10), and optional notes.

4. **Sleep & Recovery Logs**:
   - Nightly duration (hours), bedtime hour, self-reported sleep quality (1-10), and lifestyle hygiene factors (caffeine, pre-bed screen time, stress levels).

5. **Productivity & Schedule Data**:
   - Scheduled tasks, focus sessions, priority levels, estimated durations, and computed focus scores.

6. **Chat & Assistant Queries**:
   - Conversation turns submitted to the health chatbot for contextual assistance.

---

## 2. Purpose and Legal Basis of Processing

- **Personalized Guidance**: Estimating BMR/TDEE, recommending meals that fit macro goals, optimizing study/exercise schedules, and providing recovery readiness scores.
- **Trend Analysis**: Showing longitudinal progress over days and weeks.
- **Safety**: Flagging severe caloric deficits or extreme workout loads without providing formal medical diagnoses.

We do **not** sell, rent, or monetize your health data.

---

## 3. Storage, Retention, and Automatic TTL

- **Local & Container Isolation**: In production, the MongoDB instance is strictly bound to an internal Docker network and is never exposed to the public internet.
- **Automated TTL Cleanup**:
  - `meals`: Purged automatically after `MONGO_MEALS_TTL_DAYS` (default 365 days).
  - `daily_logs`: Purged automatically after `MONGO_DAILY_LOGS_TTL_DAYS` of inactivity.
  - `activity_logs`: Purged automatically after `MONGO_ACTIVITY_LOGS_TTL_DAYS` (default 365 days).
  - `sleep_logs`: Purged automatically after `MONGO_SLEEP_LOGS_TTL_DAYS` (default 365 days).
  - `chat_history`: Purged automatically after `MONGO_CHAT_HISTORY_TTL_DAYS` (default 180 days).

---

## 4. Third-Party Integrations & PII Boundaries

1. **USDA Food Data Central API**:
   - Only food query strings are transmitted to fetch nutrient profiles. No user profile information or identifiers are ever shared.
2. **ExerciseDB API**:
   - Only muscle group or exercise query terms are transmitted. No personal identifiers are sent.
3. **Groq AI (Llama-3)**:
   - When configured with `GROQ_API_KEY`, user queries and anonymized health snapshot parameters (e.g. current calorie total, sleep hours) are passed to generate natural language explanations.
   - **Keyless Fallback**: When no external key is configured, all chatbot responses run entirely offline through local rule-based inference.

---

## 5. User Rights and Controls

### Right to Erasure ("Right to Be Forgotten")
Users can permanently delete their account and all associated health records at any time.
- **API**: `DELETE /api/user/<user_id>` (authenticated via session cookie and protected by CSRF).
- **Effect**: Cascades deletion across all MongoDB collections (`users`, `daily_logs`, `meals`, `activities`, `activity_logs`, `schedules`, `productivity_sessions`, `chat_history`, `sleep_logs`, `recommendations`), clears all in-memory caches, and revokes the active session.

### Right to Data Portability (Export)
Users can download a complete structured archive of all their personal records.
- **API**: `GET /api/user/<user_id>/export` (authenticated).
- **Format**: JSON file containing profile details (password hash redacted), all logged meals, activities, sleep logs, schedules, and chat history.

### Right to Rectification
Users can update their profile, weight, targets, and goals at any time via the profile settings endpoints.

---

## 6. Security Safeguards

- **Transport Security**: TLS/HTTPS termination via reverse proxy (Nginx/Caddy) with HTTP Strict Transport Security (`HSTS`).
- **Session Hardening**: Session cookies enforce `HttpOnly`, `SameSite=Lax`, and `Secure` flags.
- **CSRF Protection**: All state-changing endpoints under active sessions require a valid cryptographic `X-CSRF-Token`.
- **Secrets Management**: Enforced 32+ character secrets in production environments.
