# Fraud Analytics Dashboard (React)

Modern analytics UI for the real-time fraud detection pipeline. Reads **dbt marts** via the FastAPI **analytics API**.

## Documentation map

| Doc | Description |
| --- | ----------- |
| [../README.md](../README.md) | Project overview and quick start |
| [../docs/README.md](../docs/README.md) | Full documentation index |
| [../docs/setup.md](../docs/setup.md) | Install, Docker, service URLs, env vars |
| [../docs/demo.md](../docs/demo.md) | End-to-end demo (includes dashboard step) |
| [../docs/analytics.md](../docs/analytics.md) | dbt marts, KPI definitions, Airflow refresh |
| [../docs/architecture.md](../docs/architecture.md) | How stream, batch, and analytics layers connect |

## What this app shows

Two pages, routed from the top navigation bar:

| Page | Route | Content |
| ---- | ----- | ------- |
| **General Overview** | `/` | Fraud KPIs, currency breakdown, top users/merchants/countries, flag reasons, fraud trend |
| **Velocity Deep-Dive** | `/velocity` | Velocity buckets, scatter (amount vs speed), heatmap, share trends, repeat intervals |

Data comes from JSON endpoints under `/api/*` (proxied to the analytics API in dev). See [../analytics_api/](../analytics_api/) and [../docs/analytics.md](../docs/analytics.md) for mart and KPI details.

## Prerequisites

### Live mode (`npm run dev`)

- **Node.js 20+** (24 LTS recommended). Vite 5 fails on Node 16 with `crypto.getRandomValues is not a function`.
- **Analytics API** on port **8001** (or set `ANALYTICS_API_PORT` / `VITE_API_PROXY` in the repo `.env`)
- **dbt marts** built in Postgres (`dbt run` in `dbt_fraud/`)

### Demo mode (`npm run dev:demo`)

- Node.js 20+ only — uses **built-in mock data**, no API or database.

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

Open **http://localhost:5173**. Vite proxies `/api` and `/health` to the analytics API (port from repo `.env`, default **8001**).

If your API runs on another port (e.g. **8000**), set `ANALYTICS_API_PORT=8000` in the repo root `.env`.

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

A **Demo mode** banner appears in the UI when mock data is active.

## GitHub Pages

Workflow: [../.github/workflows/deploy-demo.yml](../.github/workflows/deploy-demo.yml) — builds demo mode on push to `main` and publishes to GitHub Pages.

1. In the repo on GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**
2. Push to `main` (or run **Deploy demo to GitHub Pages** manually under Actions)
3. Open `https://<username>.github.io/<repo-name>/`

The live demo uses mock APIs only — no Postgres or analytics API required.

## Production build

```powershell
cd frontend
npm run build
npm run preview
```

Serves the production bundle locally. Requires a running analytics API (or configure `VITE_API_URL` at build time for a fixed API host).

## Docker (full stack)

From the repo root:

```powershell
docker compose up -d --build analytics-api dashboard-web
```

Open **http://localhost:3000** — nginx serves the React app and proxies API routes.

See [../docs/setup.md § Service URLs](../docs/setup.md#service-urls) for all service URLs.

## npm scripts

| Script | Purpose |
| ------ | ------- |
| `npm run dev` | Dev server with live API proxy (port 5173) |
| `npm run dev:demo` | Dev server with mock data (`.env.demo`) |
| `npm run build` | Production build (live API mode) |
| `npm run build:demo` | Static demo build for GitHub Pages |
| `npm run preview` | Preview the last production/demo build |
| `npm run lint` | ESLint |

## Configuration

| Variable | Where | Purpose |
| -------- | ----- | ------- |
| `ANALYTICS_API_PORT` | repo `.env` | Dev proxy target port (via `vite.config.ts`) |
| `VITE_API_PROXY` | repo `.env` | Override full proxy URL |
| `VITE_API_URL` | build-time | API base URL (empty = same origin) |
| `VITE_DEMO_MODE` | `.env.demo` | Enable mock API (`true` in demo builds) |
| `VITE_BASE_PATH` | CI / shell | GitHub Pages subpath (e.g. `/repo-name/`) |
| `DASHBOARD_AUTO_REFRESH_SECONDS` | repo `.env` | Poll interval exposed via `/api/meta/status` |

## Project layout

```
frontend/
├── src/
│   ├── api/           # HTTP client, types, mock data (demo mode)
│   ├── components/    # Charts, layout, KPI cards, filters
│   ├── pages/         # GeneralOverview, VelocityDeepDive
│   ├── hooks/         # Date drill-down for trend charts
│   ├── theme/         # Brand + metric colors
│   └── utils/         # Chart tooltips, datetime axis, heatmap colors
├── public/
├── .env.demo          # Demo mode flags
├── vite.config.ts     # Dev proxy + base path for GitHub Pages
└── package.json
```

## Stack

- React 19 + TypeScript + Vite
- Tailwind CSS (brand theme from `chart_template/`)
- Recharts
- TanStack Query (auto-refresh aligned with `DASHBOARD_AUTO_REFRESH_SECONDS` in live mode)

## Related

- **Analytics API:** [../analytics_api/main.py](../analytics_api/main.py)
- **dbt marts:** [../dbt_fraud/](../dbt_fraud/)
