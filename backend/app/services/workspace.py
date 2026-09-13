from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass
class StoredDocument:
    id: str
    name: str
    company: str | None
    content: str
    created_at: str


@dataclass
class WorkspaceStore:
    documents: list[StoredDocument] = field(default_factory=list)
    reports: list[dict] = field(default_factory=list)

    def add_document(self, name: str, content: str, company: str | None) -> StoredDocument:
        document = StoredDocument(str(uuid4()), name, company, content, datetime.now(timezone.utc).isoformat())
        self.documents.insert(0, document)
        return document

    def search_documents(self, query: str, company: str | None = None) -> list[dict]:
        words = {word.lower() for word in query.split() if len(word) > 3}
        matches = []
        for document in self.documents:
            if company and document.company and document.company.upper() != company.upper():
                continue
            text = document.content.lower()
            score = sum(word in text for word in words)
            if score:
                start = min((text.find(word) for word in words if word in text), default=0)
                matches.append({"document_id": document.id, "document": document.name, "company": document.company, "excerpt": document.content[max(0, start - 100):start + 360].strip(), "score": score})
        return sorted(matches, key=lambda item: item["score"], reverse=True)[:3]


workspace = WorkspaceStore()
