from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingFailure(RuntimeError):
    pass


class EmbeddingProvider(ABC):
    dimensions: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str | None, model: str, dimensions: int):
        self.api_key = api_key
        self.model = model
        self.dimensions = dimensions

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise EmbeddingFailure("OPENAI_API_KEY is required for the configured OpenAI embedding provider.")
        try:
            from openai import OpenAI
            response = OpenAI(api_key=self.api_key, timeout=30.0, max_retries=1).embeddings.create(model=self.model, input=texts, dimensions=self.dimensions)
            return [item.embedding for item in response.data]
        except Exception as error:
            raise EmbeddingFailure(embedding_error_message(error)) from error


def embedding_error_message(error: Exception) -> str:
    """Map SDK failures to actionable, secret-safe messages."""
    name = type(error).__name__
    status = getattr(error, "status_code", None)
    if name == "AuthenticationError" or status == 401:
        return "OpenAI rejected the configured API key (401). Check OPENAI_API_KEY in the project .env file, then restart the backend."
    if name == "PermissionDeniedError" or status == 403:
        return "OpenAI denied embedding access (403). Check that this key/project can use the configured embedding model."
    if name == "RateLimitError" or status == 429:
        return "OpenAI rate limit or quota reached (429). Check project billing and limits, then retry later."
    if name == "APITimeoutError":
        return "OpenAI embedding request timed out. Check the network and retry."
    if name == "APIConnectionError":
        return "Could not connect to OpenAI for embeddings. Check internet access, proxy/firewall settings, and retry."
    if status == 400:
        return "OpenAI rejected the embedding request (400). Check the configured model, dimensions, and document text."
    return "OpenAI embedding service failed" + (f" (HTTP {status})" if status else ". Check provider status and backend network access.")
