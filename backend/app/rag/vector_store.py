from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


class VectorStoreFailure(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorMatch:
    vector_id: str
    score: float
    payload: dict


class VectorStore(ABC):
    @abstractmethod
    def upsert(self, points: list[tuple[str, list[float], dict]]) -> None: ...

    @abstractmethod
    def search(self, vector: list[float], limit: int, company: str | None = None) -> list[VectorMatch]: ...

    def delete_document(self, document_id: str) -> None:
        raise VectorStoreFailure("This vector store does not support deletion.")


class QdrantVectorStore(VectorStore):
    def __init__(self, url: str | None, collection: str, dimensions: int):
        if not url:
            raise VectorStoreFailure("QDRANT_URL is required for document indexing and semantic retrieval.")
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            self.client = QdrantClient(url=url, timeout=10)
            self.collection = collection
            if self.client.collection_exists(collection):
                info = self.client.get_collection(collection)
                configured_size = getattr(getattr(info.config.params, "vectors", None), "size", None)
                if configured_size is not None and configured_size != dimensions:
                    raise VectorStoreFailure(f"Qdrant collection vector size is {configured_size}; configured embeddings require {dimensions}.")
            else:
                self.client.create_collection(collection_name=collection, vectors_config=VectorParams(size=dimensions, distance=Distance.COSINE))
        except VectorStoreFailure:
            raise
        except Exception as error:
            raise VectorStoreFailure("Qdrant connection or collection validation failed; verify service and configuration.") from error

    def upsert(self, points: list[tuple[str, list[float], dict]]) -> None:
        try:
            from qdrant_client.models import PointStruct
            self.client.upsert(self.collection, points=[PointStruct(id=point_id, vector=vector, payload=payload) for point_id, vector, payload in points], wait=True)
        except Exception as error:
            raise VectorStoreFailure("Qdrant upsert failed; verify service availability and vector configuration.") from error

    def search(self, vector: list[float], limit: int, company: str | None = None) -> list[VectorMatch]:
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            query_filter = Filter(must=[FieldCondition(key="company", match=MatchValue(value=company.upper()))]) if company else None
            response = self.client.query_points(collection_name=self.collection, query=vector, query_filter=query_filter, limit=limit).points
            return [VectorMatch(vector_id=str(point.id), score=float(point.score), payload=point.payload or {}) for point in response]
        except Exception as error:
            raise VectorStoreFailure("Qdrant search failed; verify service availability and vector configuration.") from error

    def delete_document(self, document_id: str) -> None:
        try:
            from qdrant_client.models import FieldCondition, Filter, MatchValue
            self.client.delete(collection_name=self.collection, points_selector=Filter(must=[FieldCondition(key="document_id", match=MatchValue(value=document_id))]), wait=True)
        except Exception as error:
            raise VectorStoreFailure("Qdrant document cleanup failed; database record was preserved.") from error


class LazyQdrantVectorStore(VectorStore):
    """Connect only when vector work is requested, after document metadata is committed."""

    def __init__(self, url: str | None, collection: str, dimensions: int):
        self.url, self.collection, self.dimensions = url, collection, dimensions
        self._store: QdrantVectorStore | None = None

    def _client(self) -> QdrantVectorStore:
        if self._store is None:
            self._store = QdrantVectorStore(self.url, self.collection, self.dimensions)
        return self._store

    def upsert(self, points: list[tuple[str, list[float], dict]]) -> None:
        self._client().upsert(points)

    def search(self, vector: list[float], limit: int, company: str | None = None) -> list[VectorMatch]:
        return self._client().search(vector, limit, company)

    def delete_document(self, document_id: str) -> None:
        self._client().delete_document(document_id)
