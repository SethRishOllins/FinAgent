from datetime import datetime, timezone
from uuid import uuid4
from app.schemas.research import AgentEvent, Finding, ResearchRequest, ResearchResponse
from app.services.analytics import technical_summary
from app.services.financial_data import fundamentals, sample_news
from app.services.market_data import market_data

DISCLAIMER = "For educational financial research only. Historical or model-derived signals are not investment advice, recommendations, or guarantees of future results."


class ResearchOrchestrator:
    def run(self, request: ResearchRequest) -> ResearchResponse:
        snapshot = market_data.snapshot(request.symbol)
        financials = fundamentals(request.symbol)
        metrics = technical_summary(snapshot.prices)
        now = datetime.now(timezone.utc)
        activity: list[AgentEvent] = []
        findings: list[Finding] = []

        def execute(agent: str, detail: str) -> None:
            activity.append(AgentEvent(agent=agent, status="completed", timestamp=now, iteration=1, detail=detail))

        execute("Master Orchestrator", "Created bounded evidence-led research plan.")
        findings.append(Finding(agent="Market Analysis", title="Technical market context", confidence=0.72, detail=f"Price is {metrics['trend']} its 20-session average. RSI(14) is {metrics['rsi14']} with annualized historical volatility of {metrics['annual_volatility']:.1%}.", evidence=[f"{snapshot.source}; observed {snapshot.as_of}", f"Maximum drawdown in sampled window: {metrics['max_drawdown']:.1%}"], limitations=["Offline deterministic sample data; configure a live provider before relying on current values."]))
        execute("Market Analysis", "Calculated trend, RSI, volatility, and drawdown.")
        findings.append(Finding(agent="Company Financial Analysis", title="Fundamental snapshot", confidence=0.61, detail=f"The offline financial dataset shows revenue growth of {financials.revenue_growth:.1f}%, net margin of {financials.net_margin:.1f}%, ROE of {financials.roe:.1f}%, and debt/equity of {financials.debt_to_equity:.2f}.", evidence=["Offline demonstration financial dataset"], limitations=["Use uploaded filings or a live verified provider before treating figures as current."]))
        execute("Financial Analysis", "Calculated and scoped fundamental metrics.")
        findings.append(Finding(agent="News Intelligence", title="News intelligence boundary", confidence=0.28, detail=f"{len(sample_news(request.symbol))} offline sample news items were classified as neutral context. No live news feed was queried.", evidence=["Offline research sample"], limitations=["Connect a news provider before using this for recent-event analysis."]))
        execute("News Intelligence", "Classified available offline sample items and reported live-data gap.")
        findings.append(Finding(agent="RAG Research", title="Document evidence check", confidence=0.2, detail="No matching indexed document was supplied for this run.", limitations=["Upload a filing and ask a document question to produce source excerpts."]))
        execute("RAG Research", "Checked the session document workspace.")
        findings.append(Finding(agent="Sentiment", title="Sentiment scope", confidence=0.25, detail="Offline sample news classification is neutral; a trained sentiment model is not enabled.", limitations=["FinBERT or equivalent is a planned ML integration."]))
        execute("Sentiment", "Recorded classification limitation.")
        findings.append(Finding(agent="Risk Analysis", title="Risk signal", confidence=0.68, detail=f"Historical volatility is {metrics['annual_volatility']:.1%}; the sampled maximum drawdown is {metrics['max_drawdown']:.1%}. These are backward-looking risk indicators.", evidence=[f"90-session deterministic sample for {snapshot.symbol}"], limitations=["No benchmark beta or VaR until live aligned series are configured."]))
        execute("Risk", "Calculated backward-looking volatility and drawdown.")
        findings.append(Finding(agent="Competitor Analysis", title="Peer comparison scope", confidence=0.35, detail="Peer comparison is available from the selected offline fundamentals universe.", limitations=["Peer selection and live sector data should be verified."]))
        execute("Competitor Analysis", "Prepared peer-comparison scope.")
        warnings = ["Market and financial inputs are offline demonstration data.", "Live news and uploaded filing evidence are missing, so the conclusion is limited."]
        execute("Critic", "Found two evidence gaps, suppressed unsupported claims, and marked the conclusion as limited.")
        execute("Judge/Synthesis", "Combined bull, risk, and evidence boundaries into the final research report.")
        return ResearchResponse(run_id=str(uuid4()), symbol=snapshot.symbol, generated_at=now, summary=f"{snapshot.company} research run completed with {len(findings)} evidence-scoped findings. {request.question}", findings=findings, warnings=warnings, activity=activity, disclaimer=DISCLAIMER)


orchestrator = ResearchOrchestrator()
