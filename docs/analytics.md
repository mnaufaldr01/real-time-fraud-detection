# Analytics (dbt + dashboard)

## dbt project

`dbt_fraud` transforms OLTP tables into the Postgres **`analytics`** schema (plus `staging` / `intermediate` views). The React dashboard reads **only** marts — not raw OLTP tables.

| Layer | Schema | Examples |
| ----- | ------ | -------- |
| Staging | `staging` | `stg_transactions`, `stg_fraud_flags`, `stg_risk_scores` |
| Intermediate | `intermediate` | `int_scored_events`, `int_velocity_fraud_events`, `int_flag_reasons` |
| Marts | `analytics` | `mart_general_kpis`, `mart_flag_reasons`, velocity/trend marts |

### Local build

```powershell
# dbt CLI is in requirements.txt (main .venv)
copy dbt_fraud\profiles.example.yml dbt_fraud\profiles.yml
cd dbt_fraud; dbt run --profiles-dir .; cd ..
```

`DATABASE_URL` must point at host port **5433** when Postgres runs in Docker.

### Airflow refresh

Enable **`dbt_marts_refresh`** at http://localhost:8081. Schedule via `.env`:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `DBT_REFRESH_ENABLED` | `true` | Disable for manual-only |
| `DBT_REFRESH_INTERVAL_MINUTES` | `10` | Cron `*/N * * * *` |
| `DBT_REFRESH_SCHEDULE` | *(empty)* | Full cron override |
| `DASHBOARD_AUTO_REFRESH_SECONDS` | `60` | React dashboard poll interval (via `/api/meta/status`) |

After schedule changes:

```powershell
docker compose up -d --build airflow-scheduler airflow-webserver
```

- Airflow dbt profile: `dbt_fraud/profiles/airflow/profiles.yml` → `postgres:5432`
- Local CLI: `dbt_fraud/profiles.yml` → `localhost:5433`

## Dashboard KPIs (`mart_general_kpis`)

| Metric | Source | Meaning |
| ------ | ------ | ------- |
| `total_tx` | All scored events in lookback | Volume |
| `flagged_count` | `is_flagged` | Auto-decline + review queue |
| `fraud_count` | `is_fraud` | Auto-decline only (`block` + `strong_suspect`) |
| `fraud_rate_pct` | `fraud_count / total_tx` | Auto-decline rate |
| `review_queue_count` | `requires_user_confirmation` | Manual review tier |
| `review_share_of_actions_pct` | `review / (review + fraud_count)` | **Manual vs auto mix** (0–100%) |
| `action_count` | `review + fraud_count` | Denominator for action mix |

Open **http://localhost:5173** (React dev) or **http://localhost:3000** (Docker `dashboard-web`) — **General Overview** and **Velocity Deep-Dive**. Setup and demo mode: [frontend/README.md](../frontend/README.md). Data reloads automatically when Airflow rebuilds marts; use **Reload data** in the top bar for an immediate refresh.

## Stream vs batch comparison

```sql
SELECT rs.final_score AS stream_score, rsh.final_score AS batch_score
FROM risk_scores rs
JOIN risk_scores_history rsh ON rsh.transaction_id = rs.transaction_id
LIMIT 10;
```

Batch uses stricter `batch_v2` rules; stream uses multi-tier scoring in the consumer. See [scoring.md](scoring.md).
