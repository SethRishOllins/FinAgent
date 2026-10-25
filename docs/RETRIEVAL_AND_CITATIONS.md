# Retrieval and Citations

The configured retrieval path is OpenAI `text-embedding-3-small` (1536 dimensions by default) plus Qdrant. Configure `OPENAI_API_KEY`, `QDRANT_URL`, collection and embedding settings. There is no silent lexical fallback: unavailable services return unavailable errors. Search uses normalized query embeddings, company filtering, a configurable-in-code 0.25 similarity floor and top-k limit. Results include document ID/name, page, section, chunk index/ID, offsets, excerpt, score and method. Database state is checked before returning citations, preventing stale/deleted vector payloads from being cited.

No reranker or hybrid lexical fusion is implemented. The assistant labels output as offline semantic retrieval. It does not claim sentence-level attribution or LLM synthesis.
