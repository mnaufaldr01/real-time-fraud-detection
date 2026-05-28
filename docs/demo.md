# Demo walkthrough

## Step 1 — Infrastructure

```powershell
docker compose up -d
powershell -ExecutionPolicy Bypass -File scripts/wait-for.ps1
```

## Step 2 — Stream processing

```powershell
# Terminal 1
python -m consumer.main

# Terminal 2
python -m producer.generator
```

Kafka UI: http://localhost:8080 — topics `transactions.raw` and `transactions.scored`.

## Step 3 — Manual fraud via API

```powershell
uvicorn producer.api.main:app --port 8000

curl -X POST http://localhost:8000/transactions `
  -H "Content-Type: application/json" `
  -d '{"transaction_id":"11111111-1111-1111-1111-111111111111","user_id":"demo_user","timestamp":"2026-05-21T12:00:00Z","amount":999.99,"currency":"USD","merchant_id":"m_fraud","merchant_category":"7995","country":"US","payment_method":"card","ip_country":"RU"}'
```

## Step 4 — Inspect Postgres

```powershell
docker exec -it real-time-fraud-detection-postgres-1 psql -U fraud -d fraud_db -c `
"SELECT ff.transaction_id, risk_tier, is_fraud, is_flagged, flag_reasons, ff.ml_prob, final_score
 FROM fraud_flags ff
 JOIN risk_scores rs ON rs.transaction_id = ff.transaction_id
 WHERE ff.transaction_id = '11111111-1111-1111-1111-111111111111';"
```

## Cleanup — delete demo transaction

Requires API running and consumer having persisted the row:

```powershell
curl -X DELETE http://localhost:8000/transactions/11111111-1111-1111-1111-111111111111
```

Removes `transactions`, `risk_scores`, `fraud_flags`, and `risk_scores_history` for that ID. Kafka messages are not deleted.

## Step 5 — Dashboard + batch

```powershell
cd dbt_fraud; dbt run --profiles-dir .; cd ..

# React dashboard (recommended)
uvicorn analytics_api.main:app --host 0.0.0.0 --port 8001 --reload
# new terminal (Node 20+ — reopen terminal after `winget install OpenJS.NodeJS.LTS`)
cd frontend; npm install; npm run dev
```

Open http://localhost:5173 for the React dashboard ([frontend/README.md](../frontend/README.md)), or run the legacy Streamlit app:

```powershell
$env:PYTHONPATH = "."; streamlit run dashboard/app.py --server.port 8501
```

Airflow (http://localhost:8081): enable **`dbt_marts_refresh`**, **`fx_rate_refresh`** (`FX_API_KEY`), **`daily_rescore`**. Optional **`model_retrain_weekly`** for gated model redeploy (static PaySim/cache + synthetic anomaly — not production DB learning; see README).

After a successful retrain, restart the fraud consumer to reload promoted `models/*.joblib` bundles.

See [analytics.md](analytics.md) for KPI definitions and [frontend/README.md](../frontend/README.md) for React setup, demo mode, and GitHub Pages.
