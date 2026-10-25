# Document Processing

Supported extensions are PDF, TXT, Markdown, DOCX and CSV. Maximum upload size defaults to 10 MB (`MAX_UPLOAD_BYTES`). PDF extraction uses pypdf and preserves one-based page numbers; DOCX uses python-docx and preserves heading sections; text/Markdown require valid UTF-8 and detect simple headings; CSV serializes each data row as named column/value pairs so metric and period remain associated.

Empty, malformed, unsupported and non-text documents are rejected with controlled messages. Scanned/image-only PDFs are not OCRed; they receive an explicit OCR-required error. Original bytes are not retained. Extraction is isolated in `app.rag.parser`; chunking uses word boundaries, 280-word windows and 40-word overlap by default, and records source offsets, page and section.

If embedding fails, the document remains listed as `failed` with an actionable, secret-safe provider message. Check the OpenAI key, project embedding access/quota, and backend network access; restart the backend after changing `.env`, then upload the same file again to retry indexing.
