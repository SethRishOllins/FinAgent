from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.providers.models import ProviderResult
from app.schemas.research import AgentEvent, Finding, ResearchRequest, ResearchResponse
from app.services.analytics import technical_summary
from app.services.live_data import LiveDataService

DISCLAIMER = "For educational financial research only. FinAgent does not provide investment recommendations, guarantees, or trading instructions."


def _source(result: ProviderResult) -> dict:
    return {
        "status": result.status,
        "source": result.provenance.source if result.provenance else None,
        "retrieved_at": result.provenance.retrieved_at if result.provenance else None,
        "data_timestamp": result.provenance.data_timestamp if result.provenance else None,
        "error": result.error.model_dump() if result.error else None,
    }


class ResearchOrchestrator:
    def __init__(self, live_data: LiveDataService):
        self.live_data = live_data

    def run(self, request: ResearchRequest, document_evidence: list[dict] | None = None) -> ResearchResponse:
        symbol = request.symbol.strip().upper()
        now = datetime.now(timezone.utc)
        activity: list[AgentEvent] = []
        findings: list[Finding] = []
        warnings: list[str] = []

        def execute(agent: str, detail: str, status: str = "completed") -> None:
            activity.append(AgentEvent(agent=agent, status=status, timestamp=now, iteration=1, detail=detail))

        execute("Research coordinator", "Created a bounded research plan and requested independently sourced evidence.")
        market = self.live_data.market(symbol)
        profile = self.live_data.profile(symbol)
        financials = self.live_data.financials(symbol)
        company_name = profile.data.name if profile.data else None
        news = self.live_data.news(symbol, company_name)
        provenance = {"market": _source(market), "profile": _source(profile), "financials": _source(financials), "news": _source(news)}

        if market.data and len(market.data.bars) >= 20:
            prices = [bar.close for bar in market.data.bars]
            metrics = technical_summary(prices)
            findings.append(Finding(agent="Market analysis", title="Historical market context", confidence_label="medium", detail=f"The last observed close is {market.data.current_price or prices[-1]:.2f}. It is {metrics['trend']} its 20-session average; RSI(14) is {metrics['rsi14']} and annualized historical volatility is {metrics['annual_volatility']:.1%}.", evidence=[f"{market.provenance.source} market history retrieved at {market.provenance.retrieved_at.isoformat()}"], limitations=["Technical indicators describe historical price behavior and are not forecasts."]))
            execute("Market analysis", f"Calculated technical indicators from {len(prices)} verified historical close values.")
        else:
            message = market.error.message if market.error else "Market data was not available."
            findings.append(Finding(agent="Market analysis", title="Market data unavailable", confidence_label="unavailable", detail="No price-based conclusion was generated because live market evidence was unavailable.", limitations=[message]))
            warnings.append(message)
            execute("Market analysis", "Skipped technical calculations because no verified OHLCV history was available.", "unavailable")

        if financials.data:
            values = financials.data
            available = [f"{key.replace('_', ' ')}: {value:.3g}" for key, value in values.calculated.items() if value is not None]
            findings.append(Finding(agent="Financial analysis", title="Reported financial statement context", confidence_label="medium", detail="Calculated metrics are derived only from fields returned by the financial provider: " + ("; ".join(available) if available else "no calculated ratios were available."), evidence=[f"Reported financial fields: {', '.join(key for key, value in values.reported.items() if value is not None) or 'none'}", f"{financials.provenance.source} statement retrieval at {financials.provenance.retrieved_at.isoformat()}"], limitations=["Missing fields remain unavailable and are not estimated."]))
            execute("Financial analysis", "Normalized reported statement fields and calculated ratios only where both operands were present.")
        else:
            message = financials.error.message if financials.error else "Financial statement data was not available."
            findings.append(Finding(agent="Financial analysis", title="Financial data unavailable", confidence_label="unavailable", detail="No fundamental conclusion was generated because verified financial statements were unavailable.", limitations=[message]))
            warnings.append(message)
            execute("Financial analysis", "Skipped ratio analysis because reported statement data was unavailable.", "unavailable")

        if news.data is not None:
            findings.append(Finding(agent="News intelligence", title="Live news coverage", confidence_label="medium" if news.data else "low", detail=f"{len(news.data)} recent articles were returned for the configured query. Articles are listed with publisher, timestamp, and URL; FinAgent does not treat headlines as verified financial facts.", evidence=[article.url for article in news.data[:3]], limitations=["News-provider coverage, relevance, and licensing constraints may limit completeness."]))
            execute("News intelligence", f"Normalized {len(news.data)} provider article records with source links.")
        else:
            message = news.error.message if news.error else "News data was not available."
            findings.append(Finding(agent="News intelligence", title="Live news unavailable", confidence_label="unavailable", detail="No current-event conclusion was generated because the live news provider was unavailable.", limitations=[message]))
            warnings.append(message)
            execute("News intelligence", "Reported live news provider status without substituting sample articles.", "unavailable")

        document_evidence = document_evidence or []
        if document_evidence:
            for item in document_evidence:
                reference = f"{item['document']}" + (f", page {item['page']}" if item.get("page") else "") + (f", {item['section']}" if item.get("section") else "")
                findings.append(Finding(agent="Document research", title=f"Uploaded source: {item['document']}", confidence_label="medium", detail=item["excerpt"], evidence=[reference, f"Chunk {item.get('chunk_index')} · semantic score {item.get('score')}"], limitations=["Document-derived content; verify the cited source excerpt and reporting period."]))
            execute("Document research", f"Retrieved {len(document_evidence)} semantically relevant, indexed document passage(s) for {symbol}.")
        else:
            findings.append(Finding(agent="Document research", title="No relevant uploaded evidence", confidence_label="unavailable", detail="No indexed document passage met the relevance threshold for this research request. This run makes no filing-based claim.", limitations=["No document-derived conclusion was added."]))
            execute("Document research", f"No relevant indexed document passages were retrieved for {symbol}.", "unavailable")
        availability = [f"{name}: {source['status']}" for name, source in provenance.items()]
        execute("Critic review", "Checked evidence availability and withheld unsupported conclusions.")
        execute("Synthesis", "Produced an evidence-scoped summary with source states and limitations.")
        name = company_name or symbol
        summary = f"Research for {name} completed. Source status: {', '.join(availability)}. {request.question}"
        if not warnings:
            warnings.append("Review source timestamps and original filings/articles before making financial decisions.")
        return ResearchResponse(run_id=str(uuid4()), symbol=symbol, generated_at=now, summary=summary, findings=findings, warnings=warnings, activity=activity, provenance=provenance, disclaimer=DISCLAIMER)
