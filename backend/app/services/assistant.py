from app.agents.orchestrator import DISCLAIMER, orchestrator
from app.schemas.research import ChatRequest, ResearchRequest
from app.services.workspace import workspace


def answer(request: ChatRequest) -> dict:
    """Grounded offline assistant. It refuses to invent external facts or investment advice."""
    message = request.message.strip()
    symbol = request.symbol.upper() if request.symbol else None
    citations = workspace.search_documents(message, symbol)
    lower = message.lower()
    if any(term in lower for term in ("buy", "sell", "invest", "should i")):
        text = "I can help you compare evidence, risk, and historical signals, but I cannot tell you what to buy or sell. A useful next step is to review diversification, data freshness, and your financial goals."
    elif citations:
        text = "I found relevant material in your uploaded documents. The excerpts below are the evidence I can use; review the source before drawing a conclusion."
    elif symbol or any(company in lower for company in ("reliance", "tcs", "hdfc")):
        resolved = symbol or next((company.upper() for company in ("reliance", "tcs", "hdfcbank") if company in lower), "RELIANCE")
        try:
            report = orchestrator.run(ResearchRequest(symbol=resolved, question=message))
            text = report.summary + " Key limitation: " + report.warnings[0]
        except ValueError:
            text = "I do not recognize that symbol in the current offline data provider. Try RELIANCE, TCS, or HDFCBANK, or connect a live provider."
    else:
        text = "I can explain portfolio concentration, summarize an uploaded document, or run an evidence-scoped research brief for RELIANCE, TCS, or HDFCBANK. What would you like to understand?"
    return {"answer": text, "citations": citations, "mode": "grounded-offline-assistant", "disclaimer": DISCLAIMER}
