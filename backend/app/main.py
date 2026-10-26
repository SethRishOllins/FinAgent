from __future__ import annotations

from contextlib import asynccontextmanager
import logging
from threading import Thread
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.agents.orchestrator import ResearchOrchestrator
from app.agents.council import CouncilOrchestrator
from app.core.config import settings
from app.db.repository import list_documents, list_reports, save_provenance, save_research, upsert_company
from app.db.models import Company, CouncilSession
from app.db.session import SessionLocal, get_session, init_database
from app.rag.embeddings import EmbeddingFailure
from app.rag.parser import DocumentParseError
from app.rag.vector_store import VectorStoreFailure
from app.schemas.research import AddCompanyRequest, ChatRequest, DocumentTextRequest, PortfolioRequest, ResearchRequest
from app.schemas.council import CouncilRequest, CouncilSessionView, CouncilStage
from sqlalchemy import select
from uuid import uuid4
from app.services.analytics import backtest_ma_crossover, forecast_experiment, portfolio_risk, risk_profile, technical_summary
from app.services.assistant import answer
from app.services.container import ServiceContainer, build_container


def _serialize(result):
    return result.model_dump(mode="json")


def _unavailable_detail(error: Exception) -> HTTPException:
    return HTTPException(status_code=503, detail={"status": "UNAVAILABLE", "message": str(error)})


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Schema changes are owned by Alembic; startup never races a deployment migration.
    if settings.database_url.startswith("sqlite"):
        # Keeps the credential-free local mode usable. PostgreSQL remains migration-owned.
        init_database()
    app.state.services = build_container()
    yield


app = FastAPI(title="FinAgent API", version="1.0.0", lifespan=lifespan)
logger = logging.getLogger("finagent.api")
app.add_middleware(CORSMiddleware, allow_origins=[item.strip() for item in settings.cors_origins.split(",")], allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(Exception)
async def unexpected_error(request: Request, error: Exception):
    logger.exception("Unhandled API error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": {"status": "INTERNAL_ERROR", "message": "The API could not complete this request. Check the backend terminal for details."}})


@app.exception_handler(SQLAlchemyError)
async def database_error(request: Request, error: SQLAlchemyError):
    message = str(error).lower()
    logger.error("Database request failed on %s %s: %s", request.method, request.url.path, type(error).__name__)
    if "does not exist" in message or "undefinedtable" in message:
        return JSONResponse(status_code=503, content={"detail": {"status": "DATABASE_SCHEMA_NOT_READY", "message": "FinAgent database migrations are not applied. Start PostgreSQL, then run `python -m alembic upgrade head` from the backend folder."}})
    return JSONResponse(status_code=503, content={"detail": {"status": "DATABASE_UNAVAILABLE", "message": "FinAgent cannot connect to its configured database. Start PostgreSQL and verify DATABASE_URL in the project .env file, then retry."}})


def services() -> ServiceContainer:
    return app.state.services


def orchestrator(container: ServiceContainer = Depends(services)) -> ResearchOrchestrator:
    return ResearchOrchestrator(container.live_data)


def _council_view(row: CouncilSession) -> dict:
    return {"id": row.id, "question": row.question, "symbol": row.symbol, "status": row.status, "stage": row.stage, "created_at": row.created_at, "updated_at": row.updated_at, "report": row.report, "findings": row.findings, "evidence": row.evidence, "debate": row.debate, "events": row.events, "failure_reason": row.failure_reason}


def _run_council_session(session_id: str, request: CouncilRequest, container: ServiceContainer) -> None:
    db = SessionLocal()
    try:
        row = db.get(CouncilSession, session_id)
        if row:
            CouncilOrchestrator(container).run(row, db, request)
    except Exception:
        logger.exception("Background AI Council task failed for %s", session_id)
    finally:
        db.close()


@app.post("/api/v1/council", status_code=202)
def create_council(request: CouncilRequest, session: Session = Depends(get_session), container: ServiceContainer = Depends(services)):
    now = datetime.now(timezone.utc)
    row = CouncilSession(id=str(uuid4()), question=request.question, symbol=request.symbol, request_json=request.model_dump(mode="json"), status=CouncilStage.CREATED.value, stage=CouncilStage.CREATED.value, created_at=now, updated_at=now)
    row.events = [{"type": "session_created", "stage": CouncilStage.CREATED.value, "detail": "Persisted a new AI Council session.", "timestamp": row.created_at.isoformat()}]
    session.add(row)
    session.commit()
    Thread(target=_run_council_session, args=(row.id, request, container), name=f"council-{row.id[:8]}", daemon=True).start()
    return {"id": row.id, "status": row.status, "stage": row.stage}


@app.get("/api/v1/council")
def council_history(session: Session = Depends(get_session)):
    rows = session.scalars(select(CouncilSession).order_by(CouncilSession.created_at.desc()).limit(100)).all()
    return [{"id": row.id, "question": row.question, "symbol": row.symbol, "status": row.status, "stage": row.stage, "created_at": row.created_at, "updated_at": row.updated_at} for row in rows]


@app.get("/api/v1/council/{session_id}")
def council_session(session_id: str, session: Session = Depends(get_session)):
    row = session.get(CouncilSession, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Council session not found.")
    return _council_view(row)


@app.get("/api/v1/council/{session_id}/report")
def council_report(session_id: str, session: Session = Depends(get_session)):
    row = session.get(CouncilSession, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Council session not found.")
    if not row.report:
        raise HTTPException(status_code=409, detail={"status": row.status, "message": row.failure_reason or "The report is not available yet."})
    return row.report


@app.get("/health")
def health(container: ServiceContainer = Depends(services)):
    return {"status": "ok", "data_mode": settings.data_mode, "database": settings.database_url.split(":", 1)[0], "cache": container.live_data.cache.health(), "providers": {"market": settings.market_provider, "financials": settings.financial_provider, "profile": settings.profile_provider, "news": settings.news_provider, "embeddings": settings.embedding_provider}}


@app.get("/api/v1/companies/saved")
def saved_companies(session: Session = Depends(get_session)):
    rows = session.scalars(select(Company).order_by(Company.symbol)).all()
    return [{"symbol": row.symbol, "name": row.name, "exchange": row.exchange, "sector": row.sector, "updated_at": row.updated_at} for row in rows]


@app.post("/api/v1/companies", status_code=201)
def add_company(request: AddCompanyRequest, session: Session = Depends(get_session), container: ServiceContainer = Depends(services)):
    symbol = request.normalized_symbol()
    result = container.live_data.profile(symbol)
    if not result.data:
        message = result.error.message if result.error else f"The configured company profile provider could not verify {symbol}."
        raise HTTPException(status_code=422, detail={"status": result.status.value, "message": message})
    company = upsert_company(session, symbol, name=result.data.name, exchange=result.data.exchange, sector=result.data.sector)
    session.commit()
    return {"symbol": company.symbol, "name": company.name, "exchange": company.exchange, "sector": company.sector, "status": result.status.value, "source": result.provenance.source if result.provenance else None, "updated_at": company.updated_at}


@app.get("/api/v1/companies")
def companies(query: str = "", container: ServiceContainer = Depends(services)):
    return _serialize(container.live_data.providers.market.search(query))


@app.get("/api/v1/companies/{symbol}/overview")
def overview(symbol: str, session: Session = Depends(get_session), container: ServiceContainer = Depends(services)):
    market = container.live_data.market(symbol)
    profile = container.live_data.profile(symbol)
    financials = container.live_data.financials(symbol)
    for result in (market, profile, financials):
        if result.provenance:
            payload = result.provenance.model_dump(mode="json")
            payload["status"] = result.status
            save_provenance(session, payload)
    if profile.data:
        upsert_company(session, symbol, name=profile.data.name, exchange=profile.data.exchange, sector=profile.data.sector)
    session.commit()
    prices = [bar.close for bar in market.data.bars] if market.data else []
    return {
        "symbol": symbol.upper(),
        "profile": _serialize(profile),
        "market": _serialize(market),
        "financials": _serialize(financials),
        "technical": technical_summary(prices) if len(prices) >= 20 else None,
        "risk": risk_profile(prices) if len(prices) >= 20 else None,
        "data_status": {"market": market.status, "financials": financials.status, "profile": profile.status},
    }


@app.post("/api/v1/research")
def research(request: ResearchRequest, session: Session = Depends(get_session), research_orchestrator: ResearchOrchestrator = Depends(orchestrator)):
    document_evidence = []
    document_warning = None
    try:
        document_evidence = services().document_service().search(session, request.question, request.symbol, limit=5)
    except (EmbeddingFailure, VectorStoreFailure) as error:
        document_warning = str(error)
    report = research_orchestrator.run(request, document_evidence)
    if document_warning:
        report.warnings.append("Document retrieval unavailable: " + document_warning)
    payload = report.model_dump(mode="json")
    save_research(session, payload, request.question)
    for value in report.provenance.values():
        if value.get("source") and value.get("retrieved_at"):
            save_provenance(session, {"symbol": request.symbol.upper(), "source": value["source"], "data_type": "research_input", "status": value["status"], "retrieved_at": value["retrieved_at"], "data_timestamp": value.get("data_timestamp"), "payload": value})
    session.commit()
    return payload


@app.post("/api/v1/portfolio/analyze")
def analyze_portfolio(request: PortfolioRequest):
    try:
        return portfolio_risk(request.holdings)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.post("/api/v1/chat")
def chat(request: ChatRequest, session: Session = Depends(get_session), container: ServiceContainer = Depends(services), research_orchestrator: ResearchOrchestrator = Depends(orchestrator)):
    try:
        documents = container.document_service()
    except VectorStoreFailure:
        documents = None
    return answer(request, research_orchestrator, session, documents)


@app.get("/api/v1/reports")
def reports(session: Session = Depends(get_session)):
    return list_reports(session)


@app.get("/api/v1/documents")
def documents(session: Session = Depends(get_session)):
    try:
        return [{"id": document.id, "name": document.name, "company": document.company_symbol, "created_at": document.created_at, "status": document.status, "error": document.ingestion_error, "content_type": document.content_type, "metadata": document.metadata_json, "chunks": len(document.chunks)} for document in list_documents(session)]
    except SQLAlchemyError as error:
        session.rollback()
        raise HTTPException(status_code=503, detail={"status": "DATABASE_NOT_READY", "message": "FinAgent database tables are missing or unavailable. From the backend folder, run: .\\.venv\\Scripts\\python.exe -m alembic upgrade head, then restart the API."}) from error


@app.post("/api/v1/documents/text")
def add_document_text(request: DocumentTextRequest, session: Session = Depends(get_session), container: ServiceContainer = Depends(services)):
    try:
        document = container.document_service().ingest(session, request.name, request.content.encode("utf-8"), request.company, "text/plain")
        return {"id": document.id, "name": document.name, "status": document.status, "metadata": document.metadata_json}
    except DocumentParseError as error:
        raise HTTPException(status_code=422, detail={"status": "INVALID_DOCUMENT", "message": str(error)}) from error
    except (EmbeddingFailure, VectorStoreFailure) as error:
        raise _unavailable_detail(error) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise HTTPException(status_code=503, detail={"status": "DATABASE_NOT_READY", "message": "FinAgent database tables are missing or unavailable. From the backend folder, run: .\\.venv\\Scripts\\python.exe -m alembic upgrade head, then restart the API."}) from error


@app.post("/api/v1/documents/upload")
async def upload_document(file: UploadFile, company: str | None = None, session: Session = Depends(get_session), container: ServiceContainer = Depends(services)):
    try:
        filename = file.filename or "uploaded-document"
        if not filename.lower().endswith((".pdf", ".txt", ".md", ".docx", ".csv")):
            raise HTTPException(status_code=415, detail={"status": "UNSUPPORTED_MEDIA_TYPE", "message": "Supported document formats are PDF, TXT, Markdown, DOCX, and CSV."})
        content = await file.read(settings.max_upload_bytes + 1)
        if len(content) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail={"status": "PAYLOAD_TOO_LARGE", "message": f"Uploads are limited to {settings.max_upload_bytes} bytes."})
        document = container.document_service().ingest(session, filename, content, company, file.content_type)
        return {"id": document.id, "name": document.name, "status": document.status, "metadata": document.metadata_json}
    except DocumentParseError as error:
        raise HTTPException(status_code=422, detail={"status": "INVALID_DOCUMENT", "message": str(error)}) from error
    except (EmbeddingFailure, VectorStoreFailure) as error:
        raise _unavailable_detail(error) from error
    except SQLAlchemyError as error:
        session.rollback()
        raise HTTPException(status_code=503, detail={"status": "DATABASE_NOT_READY", "message": "FinAgent database tables are missing or unavailable. From the backend folder, run: .\\.venv\\Scripts\\python.exe -m alembic upgrade head, then restart the API."}) from error
    except HTTPException:
        raise
    except Exception as error:
        session.rollback()
        logger.exception("Document upload failed for %s", file.filename or "unnamed upload")
        raise HTTPException(status_code=500, detail={"status": "UPLOAD_FAILED", "message": "Document upload failed unexpectedly. Check the backend log for the request details."}) from error


@app.get("/api/v1/documents/search")
def search_documents(query: str, company: str | None = None, session: Session = Depends(get_session), container: ServiceContainer = Depends(services)):
    try:
        return {"status": "LIVE", "retrieval_mode": "semantic", "results": container.document_service().search(session, query, company)}
    except (EmbeddingFailure, VectorStoreFailure) as error:
        raise _unavailable_detail(error) from error


@app.delete("/api/v1/documents/{document_id}")
def delete_document(document_id: str, session: Session = Depends(get_session), container: ServiceContainer = Depends(services)):
    try:
        removed = container.document_service().delete(session, document_id)
    except VectorStoreFailure as error:
        raise _unavailable_detail(error) from error
    if not removed:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"id": document_id, "status": "deleted"}


@app.get("/api/v1/companies/{symbol}/news")
def news(symbol: str, container: ServiceContainer = Depends(services)):
    profile = container.live_data.profile(symbol)
    return _serialize(container.live_data.news(symbol, profile.data.name if profile.data else None))


@app.get("/api/v1/companies/{symbol}/forecast")
def forecast(symbol: str, container: ServiceContainer = Depends(services)):
    market = container.live_data.market(symbol)
    if not market.data or len(market.data.bars) < 30:
        return {"status": market.status, "error": _serialize(market).get("error"), "limitations": ["At least 30 verified historical closes are required for this transparent baseline experiment."]}
    result = forecast_experiment([bar.close for bar in market.data.bars])
    result["provenance"] = _serialize(market).get("provenance")
    result["status"] = market.status
    return result


@app.get("/api/v1/companies/{symbol}/backtest")
def backtest(symbol: str, initial_capital: float = 100000, container: ServiceContainer = Depends(services)):
    market = container.live_data.market(symbol)
    if not market.data or len(market.data.bars) < 25:
        return {"status": market.status, "error": _serialize(market).get("error"), "limitations": ["At least 25 verified historical closes are required for a moving-average backtest."]}
    result = backtest_ma_crossover([bar.close for bar in market.data.bars], initial_capital)
    result["provenance"] = _serialize(market).get("provenance")
    result["status"] = market.status
    result["limitations"] = ["Historical backtests are not forecasts and do not establish future performance."]
    return result


@app.get("/api/v1/compare")
def compare(symbols: str = "RELIANCE,TCS,INFY", container: ServiceContainer = Depends(services)):
    selected = [symbol.strip().upper() for symbol in symbols.split(",") if symbol.strip()]
    if not 2 <= len(selected) <= 5:
        raise HTTPException(status_code=422, detail="Choose between two and five companies.")
    records = []
    for symbol in selected:
        result = container.live_data.financials(symbol)
        records.append({"symbol": symbol, "status": result.status, "data": result.data.model_dump(mode="json") if result.data else None, "provenance": result.provenance.model_dump(mode="json") if result.provenance else None, "error": result.error.model_dump() if result.error else None})
    return {"companies": records, "note": "Only provider-returned financial values and directly calculated ratios are displayed."}


@app.get("/api/v1/market-overview")
def market_overview(container: ServiceContainer = Depends(services)):
    indices = []
    for label, symbol in (("NIFTY 50", "NIFTY"), ("SENSEX", "SENSEX")):
        result = container.live_data.market(symbol)
        indices.append({"name": label, "symbol": symbol, "status": result.status, "price": result.data.current_price if result.data else None, "change_pct": result.data.change_pct if result.data else None, "provenance": result.provenance.model_dump(mode="json") if result.provenance else None, "error": result.error.model_dump() if result.error else None})
    return {"indices": indices, "status": "LIVE provider results are labelled individually; unavailable values are not replaced with a market sample."}
