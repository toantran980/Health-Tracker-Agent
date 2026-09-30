# Machine Learning Models

This document describes the ML models in the AI Health & Wellness Tracker: what
they predict, how they are trained, which datasets back them, and how they
behave at runtime when a trained artifact is missing.

Trained artifacts are gitignored and written to `data/*.pkl`. The app never
requires them: every predictor falls back to a deterministic, documented
bootstrap path when its model file is absent, so the tracker runs out of the
box while models are only loaded when available.

| Model | Module (`ai_modules/`) | Runtime artifact | Training script |
| ----- | ---------------------- | ---------------- | --------------- |
| Productivity predictor | `productivity_predictor.py` | `data/productivity_model.pkl` | `models/train_model.py` |
| Sleep quality predictor | `sleep_quality_predictor.py` | `data/sleep_quality_model.pkl` | `models/train_sleep_model.py` |
| Recovery readiness predictor | `recovery_predictor.py` | `data/recovery_model.pkl` | `models/train_recovery_model.py` |
| Activity classifier | `activity_classifier.py` | `data/activity_classifier.pkl` | `models/train_activity_classifier.py` |

## Model inventory

### ProductivityPredictor

- **Task:** predict a focus score and session duration for a study slot.
- **Model:** `sklearn.ensemble.RandomForestRegressor`.
- **Features:** hour of day, day of week, sleep quality, sleep hours,
  nutrition score, energy level, previous session duration, task difficulty,
  plus simple interaction terms.
- **Training:** `python models/train_model.py` (options: `--train`, `--eval`,
  `--model`, `--incremental` for incremental updates, `--save`).
- **Evaluation data:** `data/eval.csv`; the dashboard exposes live metrics
  (MAE, RMSE, R², sample count) at `/api/metrics/productivity_predictor`
  (cached per process with a 5-minute TTL; `?refresh=1` forces a recompute).

### SleepQualityPredictor

- **Task:** predict a self-reported sleep quality score (0–10).
- **Model:** `sklearn.ensemble.RandomForestRegressor`.
- **Features:** `SleepFeatures` dataclass normalized into `[0, 1]` with
  interaction terms (bedtime distance from a reference hour, duration,
  caffeine near bedtime, pre-bed screen time, stress).
- **Training:** `python models/train_sleep_model.py` with optional
  `--csv <path>` and `--model <path>`.
- **Dataset:** Sleep Health and Lifestyle dataset (`data/external/sleep_health_and_lifestyle/`).
  Columns absent from the survey (bedtime, caffeine, screen time) use neutral
  defaults so training is driven by the real survey columns.
- **Validation:** 70/15/15 train/validation/test split; validation selects the
  best regressor family; test reports held-out metrics.
- **Runtime:** `/api/sleep/predict/<user_id>`.

### RecoveryPredictor

- **Task:** predict physical recovery / readiness for a day.
- **Model:** `sklearn.ensemble.RandomForestRegressor`; features are assembled
  by the `RecoveryFeatures` dataclass.
- **Training:** `python models/train_recovery_model.py` with optional
  `--model <path>`.
- **Dataset:** FitBit wearable data (`data/external/fitbit_dataset/`) — daily
  activity merged with sleep records to derive per-person, per-day recovery
  features.
- **Label note:** FitBit provides no true readiness label, so the training
  target uses a documented, data-derived heuristic proxy — the same formula the
  predictor's fallback path uses. The label definition is transparent and
  reproducible.
- **Validation:** 70/15/15 train/validation/test split, regressor-family
  selection on validation, held-out test metrics.
- **Runtime:** `/api/recovery/<user_id>`.

### ActivityClassifier

- **Task:** map smartphone-sensor feature vectors to one of six human activity
  labels (the UCI HAR activity set).
- **Model:** `sklearn.ensemble.RandomForestClassifier` with a
  `LabelEncoder`-decoded label space.
- **Features:** 561 raw sensor features (accelerometer + gyroscope statistics).
- **Training:** `python models/train_activity_classifier.py` with optional
  `--model <path>`.
- **Dataset:** UCI Human Activity Recognition with Smartphones
  (`data/external/UCI_HAR_Dataset/train.csv`, `test.csv`).
- **Validation:** the official UCI test split (~2,947 rows) is held out as the
  final test set; a stratified 90/10 validation carve from the official train
  split selects random-forest hyperparameters. Per-sample identifiers
  (`subject`, `Activity`) are excluded from the feature matrix.
- **Runtime:** the trained artifact is loadable via `ActivityClassifier.load_model`
  and exported through `ai_modules/__init__.py`; it is not yet wired to a
  dashboard endpoint. Sensor-data ingestion for live predictions is a
  follow-up (see [TODO.md](TODO.md)).

## External datasets & provenance

Datasets live under the gitignored `data/external/` tree. Provenance,
licenses, and preprocessing instructions are documented in
`data/external/*_metadata.json` and `data/external/*_dataset_instructions.txt`.
`data/external/download_datasets.py` drives the download. Each model trains
from its own dataset; unrelated targets are never merged into
`data/training_data.csv`.

- **Sleep Health and Lifestyle** — `data/external/sleep_health_and_lifestyle/`
- **FitBit Fitness Tracker Data** — `data/external/fitbit_dataset/`
- **UCI Human Activity Recognition** — `data/external/UCI_HAR_Dataset/`
- **PAMAP2** (future) — instructions in `data/external/pamap2_dataset_instructions.txt`

## Fallback behavior

If a `data/*.pkl` artifact is missing at runtime, the corresponding predictor:

1. Detects the absence and logs a warning.
2. Loads a deterministic bootstrap / heuristic path (e.g., `RecoveryPredictor`
   computes the same documented readiness formula the training target uses).
3. Returns usable results so nothing in the API or dashboard breaks.

This keeps local and containerized runs functional before any dataset has been
downloaded or any model trained, while still using the trained models when they
exist.