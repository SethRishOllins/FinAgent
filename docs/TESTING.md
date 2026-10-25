# Testing

## Backend

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

The suite includes analytics edge cases, beta, rolling-origin forecasting, moving-average timing/costs, explicit demo mode, cache provenance, unavailable providers, document ingestion/citations with fakes, and persistence helpers.

## Frontend

From `frontend`:

```powershell
npm.cmd run build
```

This performs TypeScript checking and the Vite production build. Browser component tests are not configured yet.

## Local runtime

For a credential-free demo, set `DATA_MODE=demo` and use SQLite. Confirm all provider badges say `DEMO`; do not use demonstration values as current market information.
