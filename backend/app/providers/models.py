from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field


class DataStatus(StrEnum):
    LIVE = "LIVE"
    CACHED = "CACHED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    DEMO = "DEMO"


class Provenance(BaseModel):
    source: str
    symbol: str | None = None
    retrieved_at: datetime
    data_timestamp: datetime | None = None
    exchange: str | None = None
    data_type: str
    url: str | None = None


class ProviderError(BaseModel):
    code: str
    message: str
    retryable: bool = False


T = TypeVar("T")


class ProviderResult(BaseModel, Generic[T]):
    status: DataStatus
    data: T | None = None
    provenance: Provenance | None = None
    error: ProviderError | None = None


class MarketBar(BaseModel):
    timestamp: datetime
    open: float | None = None
    high: float | None = None
    low: float | None = None
    close: float
    volume: int | None = None


class MarketSnapshot(BaseModel):
    symbol: str
    provider_symbol: str
    company: str | None = None
    currency: str | None = None
    bars: list[MarketBar] = Field(default_factory=list)
    current_price: float | None = None
    change_pct: float | None = None


class FinancialStatement(BaseModel):
    symbol: str
    currency: str | None = None
    reported: dict[str, float | None] = Field(default_factory=dict)
    calculated: dict[str, float | None] = Field(default_factory=dict)


class NewsArticle(BaseModel):
    title: str
    publisher: str | None = None
    published_at: datetime | None = None
    url: str
    summary: str | None = None
    relevance: str | None = None


class CompanyProfile(BaseModel):
    symbol: str
    name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None
    summary: str | None = None
