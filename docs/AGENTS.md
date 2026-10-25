# Research Workflow

The research coordinator creates a bounded investigation. Market analysis, financial analysis, and news intelligence operate on separate provider results; document research preserves its evidence boundary until indexed sources are retrieved.

The critic review records unavailable or incomplete sources, and synthesis emits a research disclaimer. The workflow is deterministic in structure, not in market content: live data is used only when the configured provider returns it, and unavailable inputs remain visible in the report.

The current workflow does not call an LLM. This is intentional: a document-grounded LLM would export retrieved excerpts to an external provider and requires an explicit deployment/data-governance decision. The existing citation-only document response is the safe offline behavior.
