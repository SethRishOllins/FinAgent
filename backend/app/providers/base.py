from __future__ import annotations

from abc import ABC, abstractmethod

from app.providers.models import CompanyProfile, FinancialStatement, MarketSnapshot, NewsArticle, ProviderResult


class ProviderFailure(RuntimeError):
    """A provider integration could not supply verified information."""

    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class MarketDataProvider(ABC):
    @abstractmethod
    def snapshot(self, symbol: str, period: str = "6mo") -> ProviderResult[MarketSnapshot]: ...

    @abstractmethod
    def search(self, query: str) -> ProviderResult[list[CompanyProfile]]: ...


class FinancialDataProvider(ABC):
    @abstractmethod
    def financials(self, symbol: str) -> ProviderResult[FinancialStatement]: ...


class NewsProvider(ABC):
    @abstractmethod
    def news(self, symbol: str, company_name: str | None = None) -> ProviderResult[list[NewsArticle]]: ...


class CompanyProfileProvider(ABC):
    @abstractmethod
    def profile(self, symbol: str) -> ProviderResult[CompanyProfile]: ...
