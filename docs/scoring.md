# Scoring pipeline

After FX conversion, each valid event passes through three scorers — **rules**, **XGBoost**, and **anomaly** — then a **multi-signal tier cascade** picks the outcome. All signals are evaluated first; the highest applicable tier wins.

Implementation: [`consumer/scoring.py`](../consumer/scoring.py), [`consumer/rules.py`](../consumer/rules.py), [`consumer/classifier.py`](../consumer/classifier.py), [`consumer/anomaly.py`](../consumer/anomaly.py).

## Tier cascade

```
hard-decline rules?               →  block
ML prob ≥ t_high?                 →  strong_suspect   (bank_transfer only)
rule_score ≥ 85?                  →  strong_suspect
2+ soft signals (ML/rules/anomaly)? →  review
1 soft signal?                    →  approve (logged as SOFT_SIGNAL_OBSERVED)
not bank_transfer, no signals?    →  out_of_scope
else                              →  approve
```

### Soft signals

Each counts independently toward review:

| Signal | Bank transfer | Card / wallet (stricter) |
| ------ | ------------- | ------------------------ |
| ML prob in `[t_low, t_high)` | Yes | N/A (ML out of scope) |
| Rule score in `[soft, 85)` | ≥ 50 | ≥ 60 |
| Anomaly score | ≥ 70 | ≥ 80 |

### Tier outcomes

| Tier | Name | `is_fraud` | `is_flagged` | User confirmation |
| ---- | ---- | ---------- | ------------ | ----------------- |
| 0 | `out_of_scope` | No | No | No — card/wallet with no soft signals |
| 1 | `block` | Yes | Yes | No — hard-decline rules |
| 2 | `strong_suspect` | Yes | Yes | No — ML ≥ `t_high` or rule score ≥ 85 |
| 3 | `review` | No | Yes | Yes — 2+ soft signals (`MULTI_SIGNAL_REVIEW`) |
| 4 | `approve` | No | No* | No — clean or single soft signal (audit logged) |

\*Single soft signals are approved but include `SOFT_SIGNAL_OBSERVED` in `flag_reasons`.

### Persisted fields

| Column | Meaning |
| ------ | ------- |
| `is_fraud` | Auto-decline: `block` or `strong_suspect` |
| `requires_user_confirmation` | Manual queue: `review` |
| `is_flagged` | Any actionable tier (`is_fraud` OR `review`) |
| `flag_reasons` | JSON audit trail (rule hits + tier drivers) |
| `risk_tier` | Tier name string |
| `final_score` | `max(rule_score, anomaly_score, ml_prob × 100)` — informational; tiers drive decisions |

## Environment variables

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `RULE_SOFT_THRESHOLD` | 50 | Min rule score for a soft rule signal |
| `RULE_STRONG_SUSPECT_THRESHOLD` | 85 | Auto-decline via rules |
| `ANOMALY_SOFT_THRESHOLD` | 70 | Anomaly soft signal (bank transfer) |
| `SOFT_SIGNALS_REQUIRED` | 2 | Soft signals needed for `review` |
| `CARD_WALLET_RULE_SOFT_THRESHOLD` | 60 | Stricter rule soft signal |
| `CARD_WALLET_ANOMALY_SOFT_THRESHOLD` | 80 | Stricter anomaly soft signal |
| `ML_THRESHOLD_LOW` / `ML_THRESHOLD_HIGH` | 0.03 / 0.22 | Env fallbacks when bundle missing |
| `VELOCITY_1H_LIMIT` | 5 | Stream velocity hard decline |
| `GLOBAL_AMOUNT_P95` / `GLOBAL_AMOUNT_P99` | 450 / 850 | Global amount fallbacks |

Classifier bundle thresholds (`threshold_low`, `threshold_high`) override ML env values when `models/fraud_classifier_v1.joblib` is loaded.

## Rulesets: `stream_v1` vs `batch_v2`

| | Stream (`stream_v1`) | Batch (`batch_v2`) |
| - | -------------------- | ------------------ |
| **Runs in** | Kafka consumer | Airflow `daily_rescore` |
| **Velocity limit** | > 5 tx/user/hour | > 3 tx/user/hour |
| **Amount P99 fallback** | Global $850 (or user P99) | Global × 0.85 |
| **Amount P95 fallback** | Global $450 (or user P95) | Global × 0.85 |
| **Output** | `risk_scores` + `fraud_flags` | `risk_scores_history` |

**Rule weights** (sum capped at 100):

| Rule | Weight | Hard decline |
| ---- | ------ | -------------- |
| `HIGH_AMOUNT` | 40 | No |
| `VELOCITY_1H` | 35 | **Yes** |
| `GEO_MISMATCH` | 50 | **Yes** |
| `NEW_MERCHANT_HIGH` | 30 | No |

**User context** (loaded from Postgres per event):

- `tx_count_1h` — rolling hour before event timestamp
- `amount_p99` / `amount_p95` — 30-day USD percentiles (global fallback if no history)
- `seen_merchants` — merchants this user has used before

## ML classifier (XGBoost)

- Trained on PaySim **TRANSFER / CASH_OUT** → scoped to `payment_method=bank_transfer`
- Bundle: `models/fraud_classifier_v1.joblib`
- Training: `analysis/paysim_training.py`, `scripts/train_fraud_classifier.py`, or `models/model-training.ipynb` (`.venv-analysis`)
- Requires **xgboost** in `.venv` (included in `requirements.txt`)
- Without bundle or xgboost: rules + anomaly only

## Anomaly score

Takes the **max** of:

1. **Z-score** — amount vs user 30-day mean/std (global fallback if no history); z ≥ 4 → 100
2. **IsolationForest** — `[amount_usd, hour_of_day, merchant_category]` from `models/anomaly_v1.joblib`

Train with: `python scripts/train_anomaly.py`

## Flag reasons

### Rule hits

| Reason | Meaning |
| ------ | ------- |
| `HIGH_AMOUNT` | `amount_usd` > user P99 (+40 rule score) |
| `VELOCITY_1H` | Hourly count exceeded (+35, hard decline) |
| `GEO_MISMATCH` | `country ≠ ip_country` (+50, hard decline) |
| `NEW_MERCHANT_HIGH` | New merchant + amount > P95 (+30) |

### Tier drivers

| Reason | Tier / role |
| ------ | ------------- |
| `HARD_DECLINE` | `block` |
| `ML_STRONG_SUSPECT` | `strong_suspect` |
| `RULE_STRONG_SUSPECT` | `strong_suspect` |
| `ML_SOFT` | Soft signal |
| `RULE_SOFT` | Soft signal |
| `ANOMALY_SOFT` | Soft signal |
| `MULTI_SIGNAL_REVIEW` | `review` |
| `SOFT_SIGNAL_OBSERVED` | `approve` (audit) |
| `OUT_OF_SCOPE` | `out_of_scope` |

### Examples

| `flag_reasons` | `risk_tier` | Interpretation |
| -------------- | ----------- | -------------- |
| `["GEO_MISMATCH", "HARD_DECLINE"]` | `block` | Auto-declined |
| `["HIGH_AMOUNT", "RULE_SOFT", "ANOMALY_SOFT", "MULTI_SIGNAL_REVIEW"]` | `review` | Two soft signals |
| `["ML_STRONG_SUSPECT"]` | `strong_suspect` | High ML confidence |
| `["HIGH_AMOUNT", "ML_SOFT", "SOFT_SIGNAL_OBSERVED"]` | `approve` | Single ML soft signal |
| `["HIGH_AMOUNT", "OUT_OF_SCOPE"]` | `out_of_scope` | Card, no soft signals |

## Inspect scores in Postgres

```powershell
docker exec -it real-time-fraud-detection-postgres-1 psql -U fraud -d fraud_db -c `
"SELECT risk_tier, is_fraud, is_flagged, requires_user_confirmation, flag_reasons, ml_prob
 FROM fraud_flags ORDER BY scored_at DESC LIMIT 10;"
```
