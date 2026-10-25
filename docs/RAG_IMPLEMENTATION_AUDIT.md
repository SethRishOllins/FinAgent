# RAG Implementation Audit

Audit date: 2026-10-25

## Observed repository state

The project already had SQLAlchemy document/chunk metadata, Alembic persistence, PDF/TXT/Markdown/CSV extraction, word-window chunking, an OpenAI embedding adapter, Qdrant upsert/search, and API upload/search routes. The assistant returned retrieved snippets without synthesis, and the research orchestrator emitted a fixed document-evidence boundary. Parsing lacked DOCX, robust malformed/empty/scanned distinctions and bounded file reads; CSV rows lost metric-period labels; retrieval had no relevance threshold or stale-document validation; vectors could not be deleted. The frontend upload surface did not list or delete documents.

## Architecture implemented in this pass

FastAPI validates an extension allowlist and bounded upload read, then dispatches to isolated format parsers. Parsing returns document pages/sections and metadata. Deterministic word-based chunking retains page, section and offsets; embeddings are provided by the configured OpenAI adapter and vectors stored/searchable in Qdrant. Search normalizes the query, applies a score threshold and verifies that the referenced database document remains indexed. Chat clearly labels semantic retrieval as offline, excerpt-based output. Company research searches semantic evidence filtered by company and includes retrieved passages as document-research findings. SQLite is available for local use and PostgreSQL via existing models/migrations.

## Acceptance criteria and current status

- PDF, TXT, Markdown, DOCX and CSV parser paths: implemented; local parser tests cover PDF malformed/scanned, CSV, and text. DOCX depends on `python-docx` and has not been exercised in this environment.
- Page/section/offset traceability and deterministic chunks: implemented; unit-tested with a parsed text fixture.
- Genuine semantic embeddings and Qdrant: wired through existing OpenAI/Qdrant adapters, but require credentials/services and were not integration-tested here. No lexical fallback is represented as semantic.
- Grounded LLM synthesis: not implemented. Assistant explicitly returns offline excerpts; no LLM is claimed.
- Citation references: returned search matches preserve document/chunk/page/section/offset and excerpt; citation integrity is checked against indexed DB records. Sentence-level claim verification is not implemented.
- Research integration: company-filtered semantic matches become report findings; no-match is explicitly reported.
- Persistence: existing SQLAlchemy models, migration and SQLite support. Original uploads are not retained. User auth/ownership is not implemented; deployment remains single-user/local-only.
- OCR: unavailable. Image-only PDFs receive a clear OCR-required parse error.
- UI: existing workspace remains. Document upload UI is being extended to show actual server state and evidence.

## Limitations

Hybrid ranking, reranking, local embeddings, LLM generation, authentication, per-user access control, retained original files, OCR, rate limiting, and browser automation tests are not complete. Qdrant/OpenAI, PostgreSQL migration, and DOCX runtime require local integration verification. Do not expose this configuration as a multi-user service.
