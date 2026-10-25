# Security

## Current controls

- API/provider secrets are backend environment values and are never bundled into the frontend.
- CORS origins are configured with `CORS_ORIGINS`.
- Pydantic validates request shapes.
- Document uploads accept only PDF, TXT, Markdown, and CSV names and are limited through `MAX_UPLOAD_BYTES`.
- Parsers treat document contents as untrusted data and never execute document instructions, code, or macros.
- Provider and retrieval failures return controlled unavailable states.
- The assistant rejects direct buy/sell requests and displays a financial-research disclaimer.
- The current document assistant is citation-only/offline. Exporting retrieved document excerpts to an external LLM provider requires explicit approval and a documented data-governance policy.

## Deployment boundary

The current API is for a single-user local workflow. Do not expose it as a multi-user system until authentication, user ownership, authorization filters, rate limiting, and audit logging are implemented and tested.

## Operational guidance

- Copy `.env.example` to `.env`; do not commit secrets.
- Use HTTPS and a restrictive CORS allowlist in deployment.
- Run Alembic migrations before a PostgreSQL deployment.
- Avoid logging secrets or raw private document contents.
