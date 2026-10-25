from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings, settings
from app.providers.registry import ProviderRegistry
from app.rag.embeddings import OpenAIEmbeddingProvider
from app.rag.service import DocumentService
from app.rag.vector_store import LazyQdrantVectorStore
from app.services.cache import RedisJsonCache
from app.services.live_data import LiveDataService


@dataclass
class ServiceContainer:
    settings: Settings
    live_data: LiveDataService

    def document_service(self) -> DocumentService:
        # Delay external connections until an upload/search actually needs them.
        return DocumentService(
            embeddings=OpenAIEmbeddingProvider(self.settings.openai_api_key, self.settings.embedding_model, self.settings.embedding_dimensions),
            vectors=LazyQdrantVectorStore(self.settings.qdrant_url, self.settings.qdrant_collection, self.settings.embedding_dimensions),
        )


def build_container(config: Settings = settings) -> ServiceContainer:
    providers = ProviderRegistry(config)
    return ServiceContainer(settings=config, live_data=LiveDataService(providers=providers, cache=RedisJsonCache(config.redis_url), settings=config))
