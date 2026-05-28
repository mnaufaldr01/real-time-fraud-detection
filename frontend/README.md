# Fraud Analytics Dashboard (React)

Modern analytics UI for the real-time fraud detection pipeline. Reads **dbt marts** via the FastAPI analytics API — same data model as the legacy Streamlit dashboard.

## Prerequisites

- **Node.js 20+** (Docker `dashboard-web` uses Node 22)
- Analytics API running on port **8001**
- dbt marts built in Postgres (`dbt run` in `dbt_fraud/`)

## Local development

```powershell
# Terminal 1 — analytics API (from repo root, venv active)
# DATABASE_URL=postgresql://fraud:fraud@localhost:5433/fraud_db
uvicorn analytics_api.main:app --host 0.0.0.0 --port 8001 --reload

# Terminal 2 — React dev server
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Vite proxies `/api` and `/health` to the analytics API.

## Production build

```powershell
npm run build
npm run preview
```

## Docker (with full stack)

```powershell
docker compose up -d --build analytics-api dashboard-web
```

Open http://localhost:3000 — nginx serves the React app and proxies API routes.

## Stack

- React 19 + TypeScript + Vite
- Tailwind CSS
- Recharts
- TanStack Query (auto-refresh aligned with `DASHBOARD_AUTO_REFRESH_SECONDS`)
