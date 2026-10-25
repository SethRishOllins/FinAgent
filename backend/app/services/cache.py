from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, TypeVar

from app.providers.models import DataStatus, ProviderResult


T = TypeVar("T")


class RedisJsonCache:
    """Small Redis cache that keeps cached provenance visible to callers."""

    def __init__(self, url: str | None):
        self.client = None
        if url:
            try:
                import redis
                self.client = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=1)
            except ImportError:
                self.client = None

    def get(self, key: str, result_type: type[T]) -> ProviderResult[T] | None:
        if self.client is None:
            return None
        try:
            raw = self.client.get(key)
            if not raw:
                return None
            result = ProviderResult[result_type].model_validate_json(raw)
            if result.provenance:
                result.status = DataStatus.CACHED
            return result
        except Exception:
            # Caching must never turn an otherwise available provider into an error.
            return None

    def set(self, key: str, result: ProviderResult, ttl_seconds: int) -> None:
        if self.client is None or result.status != DataStatus.LIVE:
            return
        try:
            self.client.setex(key, ttl_seconds, result.model_dump_json())
        except Exception:
            return

    def health(self) -> dict[str, Any]:
        if self.client is None:
            return {"configured": False, "status": "UNAVAILABLE"}
        try:
            self.client.ping()
            return {"configured": True, "status": "LIVE", "checked_at": datetime.now(timezone.utc).isoformat()}
        except Exception:
            return {"configured": True, "status": "UNAVAILABLE"}
