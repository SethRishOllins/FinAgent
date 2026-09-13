# Agents

The master orchestrator delegates narrow tasks to agents and records each event. The critic is mandatory and explicitly reports insufficient sources, low confidence, contradictions, and unavailable data. Final output always carries the financial research disclaimer.

The current runnable workflow uses deterministic offline data to make demonstrations reproducible. Live market/news/filing providers, RAG ingestion, and LLM synthesis must be configured before any live research use.
