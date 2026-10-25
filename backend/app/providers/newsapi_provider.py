from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.providers.base import NewsProvider
from app.providers.models import DataStatus, NewsArticle, ProviderError, ProviderResult, Provenance


class NewsApiProvider(NewsProvider):
    source = "NewsAPI"

    def __init__(self, api_key: str | None, timeout_seconds: float = 10.0):
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def news(self, symbol: str, company_name: str | None = None) -> ProviderResult[list[NewsArticle]]:
        now = datetime.now(timezone.utc)
        provenance = Provenance(source=self.source, symbol=symbol.upper(), retrieved_at=now, data_type="company_news", url="https://newsapi.org/v2/everything")
        if not self.api_key:
            return ProviderResult(status=DataStatus.UNAVAILABLE, provenance=provenance, error=ProviderError(code="PROVIDER_NOT_CONFIGURED", message="NEWSAPI_KEY is required to retrieve live company news."))
        query = company_name or symbol.upper()
        try:
            response = httpx.get("https://newsapi.org/v2/everything", params={"q": query, "language": "en", "sortBy": "publishedAt", "pageSize": 20}, headers={"X-Api-Key": self.api_key}, timeout=self.timeout_seconds)
            if response.status_code != 200:
                return ProviderResult(status=DataStatus.UNAVAILABLE, provenance=provenance, error=ProviderError(code="PROVIDER_RESPONSE_ERROR", message=f"News provider returned HTTP {response.status_code}.", retryable=response.status_code >= 500))
            articles = []
            for item in response.json().get("articles", []):
                url = item.get("url")
                title = item.get("title")
                if not url or not title:
                    continue
                published = item.get("publishedAt")
                articles.append(NewsArticle(title=title, publisher=(item.get("source") or {}).get("name"), published_at=datetime.fromisoformat(published.replace("Z", "+00:00")) if published else None, url=url, summary=item.get("description"), relevance="query match"))
            return ProviderResult(status=DataStatus.LIVE, data=articles, provenance=provenance)
        except (httpx.HTTPError, ValueError) as error:
            return ProviderResult(status=DataStatus.UNAVAILABLE, provenance=provenance, error=ProviderError(code="PROVIDER_REQUEST_FAILED", message=f"News provider request failed: {error}", retryable=True))
