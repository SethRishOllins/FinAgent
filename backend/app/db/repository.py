from __future__ import annotations

from datetime import datetime

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Company, DataSourceMetadata, Document, DocumentChunk, ResearchReport, ResearchRun


def upsert_company(session: Session, symbol: str, **values: str | None) -> Company:
    symbol = symbol.upper()
    company = session.get(Company, symbol)
    if company is None:
        company = Company(symbol=symbol)
        session.add(company)
    for field, value in values.items():
        if value is not None and hasattr(company, field):
            setattr(company, field, value)
    return company


def save_provenance(session: Session, payload: dict) -> None:
    retrieved_at = payload["retrieved_at"]
    data_timestamp = payload.get("data_timestamp")
    if isinstance(retrieved_at, str):
        retrieved_at = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
    if isinstance(data_timestamp, str):
        data_timestamp = datetime.fromisoformat(data_timestamp.replace("Z", "+00:00"))
    payload_json = jsonable_encoder(payload)
    session.add(DataSourceMetadata(
        company_symbol=payload.get("symbol"), source=payload.get("source", "unknown"), data_type=payload.get("data_type", "unknown"),
        status=payload.get("status", "UNAVAILABLE"), retrieved_at=retrieved_at, data_timestamp=data_timestamp, payload=payload_json,
    ))


def save_research(session: Session, response: dict, question: str) -> None:
    upsert_company(session, response["symbol"])
    run = ResearchRun(id=response["run_id"], company_symbol=response["symbol"], question=question)
    session.add(run)
    session.add(ResearchReport(
        run_id=run.id, summary=response["summary"], findings=response["findings"], warnings=response["warnings"],
        activity=response["activity"], provenance=response.get("provenance", {}),
    ))


def list_reports(session: Session) -> list[dict]:
    rows = session.scalars(select(ResearchReport).order_by(ResearchReport.created_at.desc())).all()
    return [{"id": row.id, "run_id": row.run_id, "summary": row.summary, "warnings": row.warnings, "created_at": row.created_at} for row in rows]


def find_document_by_checksum(session: Session, checksum: str) -> Document | None:
    return session.scalar(select(Document).where(Document.checksum == checksum))


def list_documents(session: Session) -> list[Document]:
    return session.scalars(select(Document).order_by(Document.created_at.desc())).all()


def document_chunks(session: Session, document_id: str) -> list[DocumentChunk]:
    return session.scalars(select(DocumentChunk).where(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index)).all()
