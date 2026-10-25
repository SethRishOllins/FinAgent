# Architecture

The React/Vite SPA calls a versioned FastAPI API. Backend flows use API routes, business services, provider interfaces, and persistence adapters so vendors remain replaceable.

`ResearchOrchestrator` requests market, profile, financial, and news evidence independently. Each result carries provenance and a `LIVE`, `CACHED`, `DEMO`, or `UNAVAILABLE` state. The critic/synthesis flow reports source gaps instead of inferring missing facts. It is a deterministic coordinator today, not a claim of autonomous LLM operation.

PostgreSQL is the system of record through SQLAlchemy and Alembic. Redis caches fresh external responses with TTL. Qdrant stores document embeddings and metadata for semantic retrieval. See [LIVE_ARCHITECTURE.md](LIVE_ARCHITECTURE.md) for the operational architecture and configuration requirements.

For a credential-free local demonstration, the application can use SQLite plus the explicit `DATA_MODE=demo` provider. Demo values are deterministic, synthetic, and never selected after a live-provider failure.
