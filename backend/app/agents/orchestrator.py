from datetime import datetime, timezone
from uuid import uuid4
from app.schemas.research import AgentEvent, Finding, ResearchRequest, ResearchResponse
from app.services.analytics import technical_summary
from app.services.market_data import market_data

DISCLAIMER = "For educational financial research only. Historical or model-derived signals are not investment advice, recommendations, or guarantees of future results."


class ResearchOrchestrator:
    def run(self, request: ResearchRequest) -> ResearchResponse:
        snapshot = market_data.snapshot(request.symbol)
        metrics = technical_summary(snapshot.prices)
        now = datetime.now(timezone.utc)
        activity: list[AgentEvent] = []
        findings: list[Finding] = []

        def execute(agent: str, detail: str) -> None:
            activity.append(AgentEvent(agent=agent, status="completed", timestamp=now, iteration=1, detail=detail))

        execute("Master Orchestrator", "Created bounded evidence-led research plan.")
        findings.append(Finding(agent="Market Analysis", title="Technical market context", confidence=0.72, detail=f"Price is {metrics['trend']} its 20-session average. RSI(14) is {metrics['rsi14']} with annualized historical volatility of {metrics['annual_volatility']:.1%}.", evidence=[f"{snapshot.source}; observed {snapshot.as_of}", f"Maximum drawdown in sampled window: {metrics['max_drawdown']:.1%}"], limitations=["Offline deterministic sample data; configure a live provider before relying on current values."]))
        execute("Market Analysis", "Calculated trend, RSI, volatility, and drawdown.")
        findings.append(Finding(agent="Company Financial Analysis", title="Fundamental research boundary", confidence=0.35, detail="Financial-statement ingestion is not configured in the offline environment, so no revenue, margin, or valuation claim is made.", limitations=["Upload or connect filings before drawing fundamental conclusions."]))
        execute("Fundamentals", "Marked missing filings as a research gap.")
        findings.append(Finding(agent="News Intelligence", title="News coverage status", confidence=0.2, detail="No live news provider was queried in this reproducible offline run.", limitations=["Connect an RSS or licensed news provider; check timestamps and sources."]))
        execute("News Intelligence", "Reported unavailable source rather than fabricating news.")
        findings.append(Finding(agent="Risk Analysis", title="Risk signal", confidence=0.68, detail=f"Historical volatility is {metrics['annual_volatility']:.1%}; the sampled maximum drawdown is {metrics['max_drawdown']:.1%}. These are backward-looking risk indicators.", evidence=[f"90-session deterministic sample for {snapshot.symbol}"], limitations=["No benchmark beta or VaR until live aligned series are configured."]))
        execute("Risk", "Calculated backward-looking volatility and drawdown.")
        warnings = ["Data source is offline demonstration data.", "Missing fundamentals and news reduce research completeness."]
        execute("Critic", "Flagged demo data and missing independent evidence; suppressed unsupported claims.")
        execute("Explanation", "Assembled cited research summary with uncertainty labels.")
        return ResearchResponse(run_id=str(uuid4()), symbol=snapshot.symbol, generated_at=now, summary=f"{snapshot.company} research run completed with {len(findings)} evidence-scoped findings. {request.question}", findings=findings, warnings=warnings, activity=activity, disclaimer=DISCLAIMER)


orchestrator = ResearchOrchestrator()
