from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents.orchestrator import DISCLAIMER, ResearchOrchestrator
from app.rag.embeddings import EmbeddingFailure
from app.rag.service import DocumentService
from app.rag.vector_store import VectorStoreFailure
from app.schemas.research import ChatRequest, ResearchRequest


def answer(request: ChatRequest, orchestrator: ResearchOrchestrator, session: Session, documents: DocumentService | None = None) -> dict:
    """Returns retrieved document evidence or a clearly bounded live-research result."""
    message = request.message.strip()
    symbol = request.symbol.upper() if request.symbol else None
    lower = message.lower()
    if any(term in lower for term in ("buy", "sell", "invest", "should i")):
        return {"answer": "I can help you compare evidence, risk, and historical signals, but I cannot tell you what to buy or sell. Review diversification, data freshness, and your own financial goals.", "citations": [], "mode": "safety-boundary", "disclaimer": DISCLAIMER}
    citations: list[dict] = []
    retrieval_warning: str | None = None
    if documents:
        try:
            citations = documents.search(session, message, symbol)
        except (EmbeddingFailure, VectorStoreFailure) as error:
            retrieval_warning = str(error)
    if citations:
        return {"answer": "Offline retrieval found the following relevant passages. This is retrieval, not an LLM-generated synthesis; use the excerpts below as evidence and draw your own conclusion.", "citations": citations, "mode": "offline-semantic-retrieval", "retrieval_mode": "semantic", "generation_status": "not_configured", "disclaimer": DISCLAIMER}
    if symbol:
        report = orchestrator.run(ResearchRequest(symbol=symbol, question=message))
        return {"answer": report.summary, "citations": [], "mode": "live-research", "provenance": report.provenance, "warning": retrieval_warning, "disclaimer": DISCLAIMER}
    return {"answer": "No sufficiently relevant indexed document evidence was found. Configure embeddings and Qdrant to search uploaded documents; include a company symbol for a provider-aware research brief.", "citations": [], "mode": "insufficient-evidence", "retrieval_mode": "semantic" if documents else "unavailable", "warning": retrieval_warning, "disclaimer": DISCLAIMER}
