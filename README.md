# FinAgent

FinAgent is an evidence-scoped financial research workspace for Indian equities. It is not investment advice and it never substitutes demonstration values when an external source is unavailable.

## What Is Implemented

- Replaceable market, financial, company-profile, and news provider contracts.
- Saved company universe: add a provider-verified ticker once and reuse it across research, comparison, forecast, and backtest views.
- Yahoo Finance integration for NSE-style symbols such as `RELIANCE` (`RELIANCE.NS`) and supported index aliases.
- NewsAPI integration, enabled only when `NEWSAPI_KEY` is configured.
- Normalized `LIVE`, `CACHED`, and `UNAVAILABLE` source states with source and retrieval timestamps.
- SQLAlchemy persistence and an initial Alembic migration for companies, users, research runs/reports, documents/chunks, portfolios/holdings, and source metadata.
- Redis JSON caching when `REDIS_URL` is configured. A cache outage is bypassed; it never fabricates or silently marks stale data as live.
- PDF, TXT, Markdown, and CSV parsing; structured chunking; configurable OpenAI embeddings; Qdrant-backed semantic retrieval with page/section citations.
- Research and chat boundaries that distinguish retrieved evidence from unavailable inputs and decline buy/sell instructions.
- AI Council local evidence workflow with persistent sessions, source-scoped retrieval, specialist evidence summaries, bounded reviewer events, and honest partial completion when LLM review is not configured.

## Local Setup

### Offline demonstration mode

This is the quickest way to run the application without market-data, news, embedding, or database credentials. Demonstration records are deterministic and visibly labelled `DEMO`; they are not live financial data.

```powershell
Copy-Item .env.example .env
Add-Content .env "`nDATA_MODE=demo`nDATABASE_URL=sqlite:///./finagent.db"
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Keep this terminal running. Confirm the API at `http://127.0.0.1:8000/health` before using the frontend.

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Every market/provider badge should display `DEMO` in this mode.

### Live-provider mode

```powershell
Copy-Item .env.example .env
docker compose up -d postgres redis qdrant
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Required Configuration By Capability

| Capability | Required setting | Behavior when absent |
| --- | --- | --- |
| Market, profile, financial statements | Network access for `yfinance` | API returns `UNAVAILABLE`; no generated values are returned. |
| Live company news | `NEWSAPI_KEY` | API returns `PROVIDER_NOT_CONFIGURED`. |
| Durable application data | `DATABASE_URL` | Run `alembic upgrade head` before starting the API; use PostgreSQL in deployments. |
| Cache | `REDIS_URL` | Cache is disabled without affecting live-provider calls. |
| Document semantic search | `OPENAI_API_KEY`, `QDRANT_URL` | Upload/search returns an explicit unavailable error. |
| AI Council evidence collection | Existing market/news providers; `OPENAI_API_KEY`, `QDRANT_URL` for selected-document retrieval | Unavailable sources are recorded; the Council completes only a partial evidence inventory. |
| AI Council generated debate / LLM evidence review | Not enabled in the current implementation | This deployment deliberately does not send private retrieved excerpts or financial data to an LLM without an explicit external data-governance approval. The interface labels this limitation and does not fabricate agent debate. |

See [docs/LIVE_ARCHITECTURE.md](docs/LIVE_ARCHITECTURE.md) for the data flow, endpoints, storage model, and operational limitations.

### AI Council

The Council page gathers available provider records and optionally searches only documents selected by the user. A migration creates persistent sessions at `/api/v1/council`; list/detail/report endpoints expose the stored findings, evidence references, events, and partial status. Apply migrations with `alembic upgrade head`. Provider and document retrieval follows the existing configuration above. The current version does not perform LLM-authored analysis or substantive cross-examination: external transmission of financial data and private document excerpts requires a deployment data-governance decision. It will not claim a genuine AI debate until that boundary is approved and implemented.

### Database schema error

If the API reports that a table such as `documents` does not exist, keep PostgreSQL running and apply the included schema migration from the `backend` directory before restarting the API:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
```

## Documentation

- [Implementation audit](docs/IMPLEMENTATION_AUDIT.md): actual feature status and acceptance boundaries.
- [Implementation status](docs/IMPLEMENTATION_STATUS.md): completed work, verification, and remaining integrations.
- [Financial methodology](docs/FINANCIAL_METHODOLOGY.md): formulas and conventions for analytics, forecasts, and backtests.
- [Data providers](docs/DATA_PROVIDERS.md): live, cache, and demo-mode behavior.
- [Security](docs/SECURITY.md): current controls and single-user deployment boundary.
- [Testing](docs/TESTING.md): exact local test/build commands.

## Important limitations

- Live-provider availability and freshness are not guaranteed; unavailable data are labelled rather than replaced with sample data.
- Document semantic search requires OpenAI embeddings and Qdrant. Supported uploads are PDF, TXT, Markdown, DOCX, and CSV. Scanned PDFs require OCR, which is not configured.
- The chat assistant currently returns clearly labelled offline retrieved excerpts; no LLM synthesis, hybrid ranking, or reranking is implemented. Uploaded text is sent to the configured embedding provider during indexing; review its data-handling terms before indexing confidential documents.
- The current API is a single-user local workflow. Authentication and record ownership are required before multi-user deployment.
