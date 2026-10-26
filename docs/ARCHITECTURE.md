# Architecture

The React/Vite SPA calls a versioned FastAPI API. Backend flows use API routes, business services, provider interfaces, and persistence adapters so vendors remain replaceable.

`ResearchOrchestrator` requests market, profile, financial, and news evidence independently. Each result carries provenance and a `LIVE`, `CACHED`, `DEMO`, or `UNAVAILABLE` state. The critic/synthesis flow reports source gaps instead of inferring missing facts. It is a deterministic coordinator today, not a claim of autonomous LLM operation.

PostgreSQL is the system of record through SQLAlchemy and Alembic. Redis caches fresh external responses with TTL. Qdrant stores document embeddings and metadata for semantic retrieval. See [LIVE_ARCHITECTURE.md](LIVE_ARCHITECTURE.md) for the operational architecture and configuration requirements.

For a credential-free local demonstration, the application can use SQLite plus the explicit `DATA_MODE=demo` provider. Demo values are deterministic, synthetic, and never selected after a live-provider failure.

## AI Council (current boundary)

`CouncilOrchestrator` reuses the existing provider adapters, deterministic analytics, and document search service. Selected document IDs are checked against indexed database records, and returned passages are retained as source references. SQLAlchemy persists one bounded session document containing its request, stage events, findings, evidence, debate/review record, report, and failure reason. Routes under `/api/v1/council` create sessions and list/read their status and report. The current API executes the bounded collection workflow during session creation, so the persisted stage events are available afterward; it does not stream live progress.

Session creation starts a bounded background worker and returns the persisted session ID immediately. The UI polls the session record and reflects its actual saved stage while the worker runs. This is a local evidence-inventory MVP, not yet the requested genuine multi-agent LLM council. The automatic approval review blocked the proposed OpenAI chat integration because it would transmit private uploaded-document excerpts and provider financial data to an external provider without explicit data-governance authorization. Consequently, the UI and report identify LLM specialist analysis, substantive cross-examination, and semantic evidence review as unavailable. Deterministic checks confirm source-reference integrity and source availability only; they do not validate factual claim correctness. No fabricated debate or generated findings are returned.
