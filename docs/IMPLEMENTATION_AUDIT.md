# FinAgent Implementation Audit

Audit date: 2026-10-25

| Feature | Current implementation | Status | Relevant files | Required modification / acceptance criterion |
| --- | --- | --- | --- | --- |
| React workspace | React/Vite pages call versioned FastAPI routes for research, market, portfolio, experiments, documents, reports, and chat. | Functional build; browser runtime still needs local verification | `frontend/src/main.tsx`, `frontend/src/workspace.css` | Add component/browser tests. |
| Market, profile, financial data | Yahoo Finance normalizes market bars, profile fields, fundamentals, timestamps, currency, and unavailable states. | Implemented; live verification needs permitted network access | `backend/app/providers/yfinance_provider.py` | Verify provider availability, rate limits, coverage, and terms in deployment. |
| Demo data | Deterministic provider is selected only by `DATA_MODE=demo`; each result carries `DEMO` status and demonstration provenance. | Implemented and tested | `backend/app/providers/demo_provider.py`, `registry.py` | Keep `DEMO` visible in every consumer UI. |
| News | NewsAPI integration preserves publisher, URL, and publication timestamp; no key returns `UNAVAILABLE`. | Implemented; credential verification pending | `backend/app/providers/newsapi_provider.py` | Configure `NEWSAPI_KEY` and verify response behavior. |
| Technical/risk analytics | SMA, EMA, Wilder RSI, volatility, drawdown, Sharpe, Sortino, historical VaR/CVaR, and covariance beta handle invalid inputs. | Implemented and unit-tested | `backend/app/services/analytics.py`, `tests/test_analytics.py` | Align asset/benchmark observations by timestamp at provider boundary for production beta. |
| Portfolio concentration | Long-only normalization returns HHI, effective holdings, largest position, and assumptions. | Implemented and unit-tested | `analytics.py`, `main.py` | Add sector/asset-class analysis only with reliable metadata. |
| Forecast experiment | Naive and trend baselines use chronological rolling-origin evaluation with measured MAE/RMSE. | Implemented and unit-tested | `analytics.py` | Add date-bearing records and advanced models only if evaluated against same baseline. |
| Backtest | Long-only MA crossover shifts close signal by one session, charges turnover cost, and returns equity/benchmark curves. | Implemented and unit-tested | `analytics.py` | Add date-bearing trade ledger and optional slippage model. |
| Research workflow | Coordinator collects provider evidence, preserves provenance, and states unavailable data. | Functional deterministic workflow; not an LLM-agent workflow | `agents/orchestrator.py` | Add a real LLM provider before claiming AI synthesis. |
| Evidence labels | Arbitrary numeric confidence was removed in favor of non-probabilistic evidence-completeness labels. | Implemented | `schemas/research.py`, `orchestrator.py`, frontend | Maintain this boundary in future findings. |
| Document/RAG | Safe PDF/TXT/Markdown/CSV parsing, chunking, embeddings, Qdrant storage, and citations exist. | Partial; semantic retrieval needs OpenAI and Qdrant | `backend/app/rag/*` | Test a real configured embedding/vector environment; add DOCX only if required. |
| Persistence | SQLAlchemy models and Alembic migration cover companies, reports, documents, portfolios, and provenance. | Local SQLite fallback works; PostgreSQL unverified here | `backend/app/db/*`, `alembic/*` | Run migration against PostgreSQL. |
| Authentication / data isolation | A User model exists, but current routes remain single-user local workflow routes. | Missing for multi-user deployment | `db/models.py`, `main.py` | Block public multi-user deployment until auth, ownership filters, and authorization tests exist. |
| Upload safety | PDF/TXT/Markdown/CSV extension allowlist and configurable 10 MB cap are enforced. | Implemented | `main.py`, `core/config.py` | Add malware/content scanning for a public deployment. |
| Cache | Redis caches only verified `LIVE` responses and labels cache hits `CACHED`. | Mock-tested; Redis service verification pending | `services/cache.py` | Start Redis and validate TTL/runtime behavior. |
| LLM / sustainability | LLM SDK settings exist but no LLM synthesis call is implemented. Sustainability source/measurement is absent. | Not implemented | `.env.example`, `services/assistant.py` | Do not describe either capability as active. |

## Engineering boundaries

- Synthetic data is never selected as a fallback after a live-provider failure.
- Missing or invalid values are represented as unavailable rather than zero.
- FinAgent provides research and risk context, not individual investment advice.
- Any live-provider, LLM, PostgreSQL, Redis, OpenAI, or Qdrant claim remains unverified until exercised with that service configured.
