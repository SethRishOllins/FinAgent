from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.db.repository import document_chunks, find_document_by_checksum, upsert_company
from app.rag.chunking import chunk_document
from app.rag.embeddings import EmbeddingFailure, EmbeddingProvider
from app.rag.parser import DocumentParseError, parse_document
from app.rag.vector_store import VectorStore, VectorStoreFailure


@dataclass
class DocumentService:
    embeddings: EmbeddingProvider
    vectors: VectorStore

    def ingest(self, session: Session, name: str, content: bytes, company: str | None, content_type: str | None = None) -> Document:
        checksum = hashlib.sha256(content).hexdigest()
        existing = find_document_by_checksum(session, checksum)
        if existing and existing.status == "indexed":
            return existing
        parsed = parse_document(name, content, content_type)
        chunks = chunk_document(parsed, document_id=checksum)
        if company:
            upsert_company(session, company)
        document = existing or Document(name=name, company_symbol=company.upper() if company else None, content_type=parsed.content_type, checksum=checksum, status="indexing", metadata_json=parsed.metadata)
        document.name = name
        document.company_symbol = company.upper() if company else None
        document.content_type = parsed.content_type
        document.status = "indexing"
        document.ingestion_error = None
        document.metadata_json = parsed.metadata
        if existing:
            session.query(DocumentChunk).filter(DocumentChunk.document_id == existing.id).delete(synchronize_session=False)
        else:
            session.add(document)
        session.flush()
        try:
            vectors = self.embeddings.embed([chunk.content for chunk in chunks])
            points = []
            records = []
            for chunk, vector in zip(chunks, vectors, strict=True):
                vector_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"finagent:{checksum}:{chunk.index}"))
                payload = {"document_id": document.id, "document": name, "company": document.company_symbol, "page": chunk.page_number, "section": chunk.section, "chunk_index": chunk.index, "content": chunk.content, "start_offset": chunk.start_offset, "end_offset": chunk.end_offset, "chunk_id": chunk.chunk_id}
                points.append((vector_id, vector, payload))
                records.append(DocumentChunk(document_id=document.id, chunk_index=chunk.index, page_number=chunk.page_number, section=chunk.section, content=chunk.content, vector_id=vector_id))
            self.vectors.upsert(points)
            session.add_all(records)
            document.status = "indexed"
            session.commit()
            return document
        except (EmbeddingFailure, VectorStoreFailure) as error:
            session.rollback()
            document = session.get(Document, existing.id if existing else document.id)
            if document is None:
                document = Document(name=name, company_symbol=company.upper() if company else None, content_type=parsed.content_type, checksum=checksum, status="failed", metadata_json=parsed.metadata)
                session.add(document)
            document.status = "failed"
            document.ingestion_error = str(error)
            session.commit()
            raise
        except Exception:
            session.rollback()
            raise

    def search(self, session: Session, query: str, company: str | None = None, limit: int = 5, threshold: float = 0.25) -> list[dict]:
        query = " ".join(query.split())
        if not query:
            return []
        vector = self.embeddings.embed([query])[0]
        matches = self.vectors.search(vector, limit=limit, company=company)
        output = []
        for item in matches:
            if item.score < threshold:
                continue
            document = session.get(Document, item.payload.get("document_id"))
            if not document or document.status != "indexed":
                continue
            output.append({"document_id": document.id, "document": document.name, "company": document.company_symbol, "page": item.payload.get("page"), "section": item.payload.get("section"), "chunk_index": item.payload.get("chunk_index"), "chunk_id": item.payload.get("chunk_id"), "start_offset": item.payload.get("start_offset"), "end_offset": item.payload.get("end_offset"), "excerpt": item.payload.get("content"), "score": round(item.score, 4), "retrieval_method": "semantic", "source": "uploaded document"})
        return output

    def delete(self, session: Session, document_id: str) -> bool:
        document = session.get(Document, document_id)
        if not document:
            return False
        self.vectors.delete_document(document_id)
        session.delete(document)
        session.commit()
        return True
