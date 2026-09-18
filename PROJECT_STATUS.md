# Project Status

## Completed
- Monorepo foundation and Windows-oriented startup guidance.
- FastAPI research API with provider boundaries, deterministic financial analytics, agent orchestration, critic, and tests.
- Interactive React workspace: dashboard, company research, portfolio concentration lab, document-ingestion prototype, and research methodology views.
- Semester 1 demonstrable research workflow with explicit offline-data, source-quality, and financial-safety boundaries.
- Expanded functional application workspace: Home, Portfolio, Markets, Company Research, Documents, Reports, Settings, and a grounded FinAgent chat assistant.
- Document text upload, in-session document search/citations, report history, and chatbot API routes.
- Python 3.13-compatible backend dependency constraints and verified API health/chat/research smoke checks.
- Company financial-analysis dataset and calculations for revenue growth, margins, EPS, ROE/ROCE, debt/equity, P/E, P/B, EV/EBITDA, free cash flow, and market cap.
- Dedicated Market Overview, Competitor Analysis, Forecasting Experiment, and Moving-Average Backtesting product flows.
- Expanded autonomous workflow with financial, RAG document, sentiment, competitor, critic, and judge/synthesis stages visible in the research report UI.

## In progress
- Connect live provider implementations after credentials/data-provider choices are configured.
- Add SQLAlchemy models, Alembic migrations, Qdrant document ingestion, and background worker as the next persistence milestone.

## Semester 1 evidence
- Architecture, API contracts, agent roles, deterministic market-data provider, technical/risk analytics, FastAPI endpoints, unit tests, and an interactive dashboard are implemented.
- The evaluation focus is traceability: the UI exposes agent stages and the backend critic explicitly suppresses unsupported claims.

## Known limitations
- The initial provider returns deterministic sample data for reproducible offline demonstrations; it must not be used as live market data.
- Forecasting, RAG embedding, and LLM synthesis are extension points, not automatically enabled without their supporting service/model.
- Uploaded documents persist for the running API process only; PostgreSQL and Qdrant persistence remain the next infrastructure milestone.
- Financial/news/market datasets are offline demonstration data. Forecasts and backtests are historical experiments, not predictions or investment recommendations.

## Verification
- `npm run build` passes for the frontend.
- `pytest` passes: 5 tests covering analytics, backtesting, document matching, and financial-advice safety behavior.
- API smoke checks pass for company overview, forecast, backtest, peer comparison, market overview, and autonomous research.
