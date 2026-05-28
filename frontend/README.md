# Fraud Analytics Dashboard (React)

Modern analytics UI for the real-time fraud detection pipeline. Reads **dbt marts** via the FastAPI analytics API — same data model as the legacy Streamlit dashboard.

## Prerequisites

- **Node.js 20+** (24 LTS recommended). Vite 5 will fail on Node 16 with `crypto.getRandomValues is not a function`.
- Analytics API running on port **8001**
- dbt marts built in Postgres (`dbt run` in `dbt_fraud/`)

### Node.js on Windows

If `node -v` shows v16 or lower:

```powershell
winget install OpenJS.NodeJS.LTS
# Close and reopen your terminal, then:
node -v   # should show v20+
```

Or use the repo helper script (picks Node 20+ from PATH):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/dev-frontend.ps1
```

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

## Demo mode (mock data, no backend)

Run the dashboard with **built-in sample data** — useful for portfolios and GitHub Pages:

```powershell
cd frontend
npm run dev:demo
```

Build the static demo bundle (same as GitHub Pages):

```powershell
cd frontend
# Optional: set base path for project pages (replace with your repo name)
$env:VITE_BASE_PATH = "/real-time-fraud-detection/"
npm run build:demo
npm run preview
```

## GitHub Pages

A workflow (`.github/workflows/deploy-demo.yml`) builds demo mode on push to `main` and publishes to **GitHub Pages**.

1. In the repo on GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. Push to `main` (or run the workflow manually)
3. Open `https://<username>.github.io/<repo-name>/`

The live demo uses mock APIs only — no Postgres or analytics API required.

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
