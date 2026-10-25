# Live FinAgent Architecture

## Data Flow

`FastAPI route -> Research/service layer -> provider contract -> external provider`

The provider contracts are `MarketDataProvider`, `FinancialDataProvider`, `CompanyProfileProvider`, and `NewsProvider`. Their normalized responses use `ProviderResult`, `Provenance`, and a status of `LIVE`, `CACHED`, or `UNAVAILABLE`. `DEMO` remains an explicit enum value for compatibility with clients, but no application route supplies demonstration data.

`LIVE` means the current process received a provider response. `CACHED` means Redis returned a result within its configured TTL. `UNAVAILABLE` includes missing credentials, provider errors, and absent infrastructure. FinAgent does not serve an expired cache as current data.

## Provider Configuration

Yahoo Finance is used through `yfinance` for historical OHLCV, current quote metadata, profile information, and statement data where the provider exposes it. Plain NSE symbols are normalized to `.NS`; `NIFTY` and `SENSEX` are mapped to provider index symbols. News is retrieved through NewsAPI only when `NEWSAPI_KEY` is set. The provider modules do not expose vendor response objects to routes or the frontend.

## Persistence

SQLAlchemy models and Alembic revision `20261007_01` create:

- `users` and `companies`
- `research_runs` and `research_reports`
- `documents` and `document_chunks`
- `portfolios` and `holdings`
- `data_source_metadata`

Run `alembic upgrade head` before starting an instance. Schema creation is intentionally owned by Alembic so application startup cannot race or bypass a migration. Production should use the PostgreSQL URL in `.env.example` and the migration workflow.

## Document Research

The document route accepts PDF, TXT, Markdown, and CSV. Parsers retain source filename, PDF page where available, and headings/sections where detectable. The chunker respects parsed page/section boundaries before applying its bounded word window. Each vector ID is deterministic from the document checksum and chunk index. Qdrant payloads include document id/name, company, page, section, chunk index, and content.

OpenAI embeddings are configured through `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIMENSIONS`, and `OPENAI_API_KEY`. The concrete `OpenAIEmbeddingProvider` and `QdrantVectorStore` are replaceable through their contracts. A failed embedding or Qdrant operation is returned as unavailable; it is not converted into a keyword result or fabricated citation.

## API Behavior

- `GET /api/v1/companies/{symbol}/overview` returns profile, market, and financial `ProviderResult` envelopes plus optional technical calculations only when sufficient verified OHLCV bars exist.
- `POST /api/v1/research` persists the bounded report and source metadata.
- `GET /api/v1/reports` reads persistent report history.
- `POST /api/v1/documents/upload` and `/text` parse, chunk, embed, and index documents when dependencies are configured.
- `GET /api/v1/documents/search` returns semantic citations including document, page, section, score, and excerpt.
- Forecast and backtest endpoints use provider-returned historical prices and report unavailable/insufficient-history states instead of generated series.

## Operational Limits

Yahoo Finance availability and field coverage are external constraints. NewsAPI requires an account/key and has plan-dependent coverage. Qdrant and OpenAI credentials are not present in this repository, so semantic document indexing cannot be verified against those real services until they are configured. The application labels each limitation at runtime.
