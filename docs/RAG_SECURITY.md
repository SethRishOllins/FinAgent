# RAG Security and Privacy

The current service is single-user and local-only. It has no authentication or ownership isolation and must not be exposed to multiple users. Upload extensions are allowlisted and the request reads at most the configured size limit plus one byte. Parsers never execute uploaded content; DOCX macros are not executed. Provider errors do not include raw SDK exception text. Uploaded content is sent to the configured embedding provider when indexing; configure provider data handling before indexing confidential material. Chat does not send retrieved excerpts to an LLM because generation is not implemented. Original files are not persisted; extracted chunk text and embeddings remain in the configured database/vector store until document deletion.

Use HTTPS, restrictive CORS, protected database/vector endpoints, backend-only secrets, and a private deployment. Authentication, rate limiting, malware scanning, and multi-user authorization are not implemented.
