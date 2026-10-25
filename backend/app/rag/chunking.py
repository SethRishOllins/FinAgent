from __future__ import annotations

from dataclasses import dataclass
import hashlib

from app.rag.parser import ParsedDocument


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    page_number: int | None
    section: str | None
    start_offset: int = 0
    end_offset: int = 0
    chunk_id: str = ""


def chunk_document(document: ParsedDocument, max_words: int = 280, overlap_words: int = 40, document_id: str | None = None) -> list[TextChunk]:
    """Chunk by parsed page/section before applying a bounded word window."""
    if max_words < 1 or overlap_words < 0 or overlap_words >= max_words:
        raise ValueError("max_words must be positive and overlap_words must be between zero and max_words - 1")
    chunks: list[TextChunk] = []
    for page in document.pages:
        import re
        matches = list(re.finditer(r"\S+", page.text))
        words = [match.group(0) for match in matches]
        start = 0
        while start < len(words):
            window = words[start:start + max_words]
            if not window:
                break
            start_offset, end_offset = matches[start].start(), matches[start + len(window) - 1].end()
            content = " ".join(window)
            index = len(chunks)
            identity = f"{document_id or document.title}:{index}:{page.page_number}:{start_offset}:{end_offset}:{content}"
            chunks.append(TextChunk(index=index, content=content, page_number=page.page_number, section=page.section, start_offset=start_offset, end_offset=end_offset, chunk_id=hashlib.sha256(identity.encode()).hexdigest()))
            if start + max_words >= len(words):
                break
            start += max_words - overlap_words
    return chunks
