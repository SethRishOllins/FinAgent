from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from app.agents.orchestrator import orchestrator
from app.core.config import settings
from app.schemas.research import ChatRequest, DocumentTextRequest, PortfolioRequest, ResearchRequest
from app.services.assistant import answer
from app.services.analytics import portfolio_risk, technical_summary
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
        return {"symbol": data.symbol, "company": data.company, "price": data.price, "change_pct": data.change_pct, "prices": data.prices, "as_of": data.as_of, "source": data.source, "technical": technical_summary(data.prices)}
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
