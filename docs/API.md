# API

- `GET /health` reports service and provider mode.
- `GET /api/v1/companies?query=reliance` discovers demo companies.
- `GET /api/v1/companies/{symbol}/overview` returns snapshot and technical metrics.
- `POST /api/v1/research` runs the bounded multi-agent research workflow.
- `POST /api/v1/portfolio/analyze` returns allocation concentration metrics.
# AI Council

# Companies

- `POST /api/v1/companies` — provider-verifies and saves a ticker in the existing companies table.
- `GET /api/v1/companies/saved` — returns the local single-user saved company list.
- `GET /api/v1/companies?query=SYMBOL` — searches/verifies a symbol through the configured market provider.

- `POST /api/v1/council` — accepts a question, optional symbol, selected indexed `document_ids`, focus, and specialist roles; returns persisted session ID/status. The bounded workflow currently runs synchronously.
- `GET /api/v1/council` — recent session history.
- `GET /api/v1/council/{session_id}` — status, events, findings, evidence, review record, and report.
- `GET /api/v1/council/{session_id}/report` — final persisted report, or `409` if unavailable.

See [Architecture](ARCHITECTURE.md#ai-council-current-boundary) for current capability limitations. Council sessions are local single-user records and are not safe for multi-user deployment without authentication and ownership enforcement.
