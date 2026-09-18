from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.agents.orchestrator import orchestrator
from app.core.config import settings
from app.schemas.research import ChatRequest, DocumentTextRequest, PortfolioRequest, ResearchRequest
from app.services.assistant import answer
from app.services.analytics import backtest_ma_crossover, forecast_experiment, portfolio_risk, risk_profile, technical_summary
from app.services.financial_data import fundamentals, peer_table, sample_news
from app.services.market_data import market_data
from app.services.workspace import workspace

app = FastAPI(title="FinAgent API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])

@app.get("/health")
def health():
    return {"status": "ok", "llm_provider": settings.llm_provider, "mode": "offline-capable"}

@app.get("/api/v1/companies")
def companies(query: str = ""):
    return market_data.search(query)

@app.get("/api/v1/companies/{symbol}/overview")
def overview(symbol: str):
    try:
        data = market_data.snapshot(symbol)
        return {"symbol": data.symbol, "company": data.company, "price": data.price, "change_pct": data.change_pct, "prices": data.prices, "as_of": data.as_of, "source": data.source, "technical": technical_summary(data.prices), "fundamentals": fundamentals(symbol).__dict__, "risk": risk_profile(data.prices), "data_status": {"market": "offline demo", "financials": "offline demo", "news": "not connected", "documents": "session workspace"}}
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

@app.post("/api/v1/research")
def research(request: ResearchRequest):
    try:
        report = orchestrator.run(request)
        workspace.reports.insert(0, report.model_dump(mode="json"))
        return report
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

@app.post("/api/v1/portfolio/analyze")
def analyze_portfolio(request: PortfolioRequest):
    try:
        return portfolio_risk(request.holdings)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/v1/chat")
def chat(request: ChatRequest):
    return answer(request)


@app.get("/api/v1/reports")
def reports():
    return workspace.reports


@app.get("/api/v1/documents")
def documents():
    return [{"id": document.id, "name": document.name, "company": document.company, "created_at": document.created_at, "characters": len(document.content)} for document in workspace.documents]


@app.post("/api/v1/documents/text")
def add_document_text(request: DocumentTextRequest):
    return workspace.add_document(request.name, request.content, request.company).__dict__


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile, company: str | None = None):
    content = (await file.read()).decode("utf-8", errors="replace")
    if len(content.strip()) < 20:
        raise HTTPException(status_code=422, detail="Upload a text-based document with at least 20 characters.")
    return workspace.add_document(file.filename or "uploaded-document.txt", content, company).__dict__


@app.get("/api/v1/documents/search")
def search_documents(query: str, company: str | None = None):
    return workspace.search_documents(query, company)


@app.get("/api/v1/companies/{symbol}/news")
def news(symbol: str):
    try:
        return sample_news(symbol)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/v1/companies/{symbol}/forecast")
def forecast(symbol: str):
    try:
        return forecast_experiment(market_data.snapshot(symbol).prices)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/v1/companies/{symbol}/backtest")
def backtest(symbol: str, initial_capital: float = 100000):
    try:
        return backtest_ma_crossover(market_data.snapshot(symbol).prices, initial_capital)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/v1/compare")
def compare(symbols: str = "RELIANCE,TCS,INFY"):
    try:
        selected = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
        if not 2 <= len(selected) <= 5:
            raise ValueError("Choose between two and five companies.")
        return {"companies": peer_table(selected), "note": "Offline demonstration fundamentals for comparative research, not investment advice."}
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/v1/market-overview")
def market_overview():
    return {"indices": [{"name": "NIFTY 50", "change": 0.64}, {"name": "NIFTY Next 50", "change": 0.31}, {"name": "SENSEX", "change": 0.52}], "sectors": [{"name": "Information Technology", "change": 0.82}, {"name": "Financial Services", "change": 0.37}, {"name": "Energy", "change": -0.21}], "status": "Offline demonstration market context; connect a live provider for current values."}
