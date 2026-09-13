# Architecture

The React/Vite SPA calls a versioned FastAPI API. The backend is layered as API -> orchestration -> agents -> provider/tool interfaces -> persistence adapters. This keeps data providers, LLMs, and storage services replaceable.

`ResearchOrchestrator` runs a bounded evidence-led flow across Market, Fundamentals, News, Risk, Critic, and Explanation roles. Typed findings preserve evidence, timestamps, confidence, and limitations. The critic flags demo or missing data and prevents unsupported claims from becoming recommendations.

PostgreSQL is intended as the system of record; Redis is cache/task state; Qdrant stores chunked document embeddings. The initial offline demo does not require them.
