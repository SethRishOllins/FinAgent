from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np

from app.providers.base import CompanyProfileProvider, FinancialDataProvider, MarketDataProvider, NewsProvider
from app.providers.models import (
    CompanyProfile,
    DataStatus,
    FinancialStatement,
    MarketBar,
    MarketSnapshot,
    NewsArticle,
    ProviderResult,
    Provenance,
)


class DemoProvider(MarketDataProvider, FinancialDataProvider, CompanyProfileProvider, NewsProvider):
    """Deterministic, explicitly labelled data for offline demos and automated tests."""

    source = "FinAgent deterministic demonstration data"

    @staticmethod
    def _symbol(symbol: str) -> str:
        return symbol.strip().upper()

    def _provenance(self, symbol: str, data_type: str) -> Provenance:
        return Provenance(
            source=self.source,
            symbol=self._symbol(symbol),
            retrieved_at=datetime.now(timezone.utc),
            data_type=data_type,
            url="https://example.invalid/finagent-demo-mode",
        )

    def snapshot(self, symbol: str, period: str = "6mo") -> ProviderResult[MarketSnapshot]:
        normalized = self._symbol(symbol)
        seed = sum(ord(character) for character in normalized)
        steps = np.arange(126, dtype=float)
        closes = 150 + (seed % 250) + 0.22 * steps + 4 * np.sin(steps / 9 + seed)
        start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=len(steps))
        bars = [MarketBar(timestamp=start + timedelta(days=index), close=round(float(close), 2), open=round(float(close - 0.6), 2), high=round(float(close + 1.2), 2), low=round(float(close - 1.4), 2), volume=1_000_000 + index * 1000) for index, close in enumerate(closes)]
        previous = bars[-2].close
        return ProviderResult(
            status=DataStatus.DEMO,
            data=MarketSnapshot(symbol=normalized, provider_symbol=f"{normalized}.DEMO", company=f"{normalized} Demonstration Company", currency="INR", bars=bars, current_price=bars[-1].close, change_pct=round((bars[-1].close / previous - 1) * 100, 4)),
            provenance=self._provenance(normalized, "demonstration_market_history"),
        )

    def profile(self, symbol: str) -> ProviderResult[CompanyProfile]:
        normalized = self._symbol(symbol)
        return ProviderResult(status=DataStatus.DEMO, data=CompanyProfile(symbol=normalized, name=f"{normalized} Demonstration Company", exchange="DEMO", sector="Demonstration sector", industry="Demonstration industry", summary="Synthetic company profile for FinAgent offline demonstration mode."), provenance=self._provenance(normalized, "demonstration_company_profile"))

    def search(self, query: str) -> ProviderResult[list[CompanyProfile]]:
        if not query.strip():
            return ProviderResult(status=DataStatus.DEMO, data=[], provenance=self._provenance("", "demonstration_symbol_search"))
        profile = self.profile(query)
        return ProviderResult(status=DataStatus.DEMO, data=[profile.data] if profile.data else [], provenance=profile.provenance)

    def financials(self, symbol: str) -> ProviderResult[FinancialStatement]:
        normalized = self._symbol(symbol)
        revenue = float(100_000 + (sum(map(ord, normalized)) % 20_000))
        operating_income, net_income, equity, debt = revenue * 0.18, revenue * 0.12, revenue * 0.75, revenue * 0.3
        reported = {"revenue": revenue, "operating_income": operating_income, "net_income": net_income, "eps": 12.5, "assets": revenue * 1.5, "liabilities": revenue * 0.75, "equity": equity, "debt": debt, "cash": revenue * 0.1, "operating_cash_flow": revenue * 0.16, "free_cash_flow": revenue * 0.11}
        calculated = {"operating_margin": operating_income / revenue, "net_margin": net_income / revenue, "roe": net_income / equity, "roa": net_income / (revenue * 1.5), "debt_to_equity": debt / equity, "pe_ratio": 18.0, "price_to_book": 2.4}
        return ProviderResult(status=DataStatus.DEMO, data=FinancialStatement(symbol=normalized, currency="INR", reported=reported, calculated=calculated), provenance=self._provenance(normalized, "demonstration_financial_statements"))

    def news(self, symbol: str, company_name: str | None = None) -> ProviderResult[list[NewsArticle]]:
        normalized = self._symbol(symbol)
        return ProviderResult(status=DataStatus.DEMO, data=[], provenance=self._provenance(normalized, "demonstration_news"))
