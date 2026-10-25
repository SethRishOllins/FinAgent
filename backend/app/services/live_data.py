from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.providers.models import CompanyProfile, FinancialStatement, MarketSnapshot, NewsArticle, ProviderResult
from app.providers.registry import ProviderRegistry
from app.services.cache import RedisJsonCache


@dataclass
class LiveDataService:
    providers: ProviderRegistry
    cache: RedisJsonCache
    settings: Settings

    def market(self, symbol: str) -> ProviderResult[MarketSnapshot]:
        key = f"finagent:market:{symbol.upper()}:6mo"
        cached = self.cache.get(key, MarketSnapshot)
        if cached:
            return cached
        result = self.providers.market.snapshot(symbol)
        self.cache.set(key, result, self.settings.market_cache_ttl_seconds)
        return result

    def financials(self, symbol: str) -> ProviderResult[FinancialStatement]:
        key = f"finagent:financials:{symbol.upper()}"
        cached = self.cache.get(key, FinancialStatement)
        if cached:
            return cached
        result = self.providers.financials.financials(symbol)
        self.cache.set(key, result, self.settings.market_cache_ttl_seconds)
        return result

    def profile(self, symbol: str) -> ProviderResult[CompanyProfile]:
        key = f"finagent:profile:{symbol.upper()}"
        cached = self.cache.get(key, CompanyProfile)
        if cached:
            return cached
        result = self.providers.profiles.profile(symbol)
        self.cache.set(key, result, self.settings.market_cache_ttl_seconds)
        return result

    def news(self, symbol: str, company_name: str | None = None) -> ProviderResult[list[NewsArticle]]:
        # News is time sensitive; cache briefly and retain the cached state in the API response.
        key = f"finagent:news:{symbol.upper()}"
        cached = self.cache.get(key, list[NewsArticle])
        if cached:
            return cached
        result = self.providers.news.news(symbol, company_name)
        self.cache.set(key, result, min(self.settings.market_cache_ttl_seconds, 120))
        return result
