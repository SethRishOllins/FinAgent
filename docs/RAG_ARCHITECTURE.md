# RAG Architecture

Upload requests pass through FastAPI size/extension checks, then isolated PDF, UTF-8 text/Markdown, DOCX, or CSV parsers. Parsed pages/sections are chunked deterministically (280 words with 40-word overlap by default), embedded by the OpenAI adapter, and upserted into Qdrant with source metadata. SQLAlchemy persists document/chunk records. Retrieval embeds a normalized query, searches Qdrant, applies a cosine-score floor (0.25 by default), and rejects references to missing or non-indexed database records.

The current assistant is intentionally offline: it returns retrieved excerpts with citations, not a generated answer. Company research supplies company-filtered retrieval results to the document-research stage. SQLite supports local runs; PostgreSQL is configured by the existing Alembic-managed schema. The deployment remains single-user/local-only.
