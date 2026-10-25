from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.providers.base import CompanyProfileProvider, FinancialDataProvider, MarketDataProvider
from app.providers.models import (
    CompanyProfile,
    DataStatus,
    FinancialStatement,
    MarketBar,
    MarketSnapshot,
    ProviderError,
    ProviderResult,
    Provenance,
)


INDEX_ALIASES = {"NIFTY": "^NSEI", "NIFTY50": "^NSEI", "SENSEX": "^BSESN"}


def provider_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if normalized in INDEX_ALIASES:
        return INDEX_ALIASES[normalized]
    return normalized if "." in normalized or normalized.startswith("^") else f"{normalized}.NS"


def _unavailable(symbol: str, data_type: str, code: str, message: str, retryable: bool = False) -> ProviderResult[Any]:
    return ProviderResult(
        status=DataStatus.UNAVAILABLE,
        error=ProviderError(code=code, message=message, retryable=retryable),
        provenance=Provenance(source="Yahoo Finance", symbol=symbol, retrieved_at=datetime.now(timezone.utc), data_type=data_type),
    )


def _number(value: Any) -> float | None:
    try:
        if value is None:
            return None
        result = float(value)
        return result if result == result else None  # NaN is not an available value.
    except (TypeError, ValueError):
        return None


class YahooFinanceProvider(MarketDataProvider, FinancialDataProvider, CompanyProfileProvider):
    """Normalizes yfinance responses without exposing its objects beyond this module."""

    source = "Yahoo Finance"

    def _ticker(self, symbol: str):
        try:
            import yfinance as yf
        except ImportError as error:  # pragma: no cover - exercised by deployment configuration
            raise RuntimeError("yfinance is not installed") from error
        return yf.Ticker(provider_symbol(symbol))

    def snapshot(self, symbol: str, period: str = "6mo") -> ProviderResult[MarketSnapshot]:
        requested = symbol.strip().upper()
        now = datetime.now(timezone.utc)
        try:
            ticker = self._ticker(requested)
            history = ticker.history(period=period, auto_adjust=False)
            if history is None or history.empty:
                return _unavailable(requested, "market_history", "EMPTY_RESPONSE", "The market provider returned no OHLCV data for this symbol.")
            bars = []
            for index, row in history.iterrows():
                timestamp = index.to_pydatetime()
                if timestamp.tzinfo is None:
                    timestamp = timestamp.replace(tzinfo=timezone.utc)
                bars.append(MarketBar(
                    timestamp=timestamp,
                    open=_number(row.get("Open")), high=_number(row.get("High")), low=_number(row.get("Low")),
                    close=float(row["Close"]), volume=int(row["Volume"]) if _number(row.get("Volume")) is not None else None,
                ))
            # fast_info is optional and can fail independently of the chart history
            # (Yahoo sometimes omits currentTradingPeriod in its quote metadata).
            try:
                info = getattr(ticker, "fast_info", {}) or {}
                current = _number(info.get("lastPrice")) or bars[-1].close
                previous = _number(info.get("previousClose"))
                exchange = info.get("exchange") or None
                currency = info.get("currency")
            except Exception:
                info = {}
                current = bars[-1].close
                previous = None
                exchange = None
                currency = None
            change = ((current / previous) - 1) * 100 if previous and previous != 0 else None
            return ProviderResult(
                status=DataStatus.LIVE,
                data=MarketSnapshot(symbol=requested, provider_symbol=provider_symbol(requested), company=None, currency=currency, bars=bars, current_price=current, change_pct=change),
                provenance=Provenance(source=self.source, symbol=requested, retrieved_at=now, data_timestamp=bars[-1].timestamp, exchange=exchange, data_type="market_history"),
            )
        except Exception as error:
            return _unavailable(requested, "market_history", "PROVIDER_REQUEST_FAILED", f"Market provider request failed: {error}", retryable=True)

    def profile(self, symbol: str) -> ProviderResult[CompanyProfile]:
        requested = symbol.strip().upper()
        try:
            ticker = self._ticker(requested)
            info = ticker.info or {}
            if not info:
                return _unavailable(requested, "company_profile", "EMPTY_RESPONSE", "The profile provider returned no company profile.")
            return ProviderResult(
                status=DataStatus.LIVE,
                data=CompanyProfile(symbol=requested, name=info.get("longName") or info.get("shortName"), exchange=info.get("exchange"), sector=info.get("sector"), industry=info.get("industry"), summary=info.get("longBusinessSummary")),
                provenance=Provenance(source=self.source, symbol=requested, retrieved_at=datetime.now(timezone.utc), exchange=info.get("exchange"), data_type="company_profile"),
            )
        except Exception as error:
            return _unavailable(requested, "company_profile", "PROVIDER_REQUEST_FAILED", f"Company profile request failed: {error}", retryable=True)

    def search(self, query: str) -> ProviderResult[list[CompanyProfile]]:
        cleaned = query.strip()
        if not cleaned:
            return ProviderResult(status=DataStatus.LIVE, data=[], provenance=Provenance(source=self.source, retrieved_at=datetime.now(timezone.utc), data_type="symbol_search"))
        # Direct NSE lookup is deterministic for a supplied symbol; it does not claim a curated company universe.
        profile = self.profile(cleaned)
        if profile.data:
            return ProviderResult(status=profile.status, data=[profile.data], provenance=profile.provenance, error=profile.error)
        return ProviderResult(status=profile.status, data=[], provenance=profile.provenance, error=profile.error)

    def financials(self, symbol: str) -> ProviderResult[FinancialStatement]:
        requested = symbol.strip().upper()
        try:
            ticker = self._ticker(requested)
            info = ticker.info or {}
            income = ticker.income_stmt
            balance = ticker.balance_sheet
            cashflow = ticker.cashflow

            def latest(frame: Any, labels: list[str]) -> float | None:
                if frame is None or getattr(frame, "empty", True):
                    return None
                for label in labels:
                    if label in frame.index:
                        return _number(frame.loc[label].iloc[0])
                return None

            reported = {
                "revenue": latest(income, ["Total Revenue", "Operating Revenue"]),
                "operating_income": latest(income, ["Operating Income", "EBIT"]),
                "net_income": latest(income, ["Net Income", "Net Income Common Stockholders"]),
                "eps": _number(info.get("trailingEps")),
                "assets": latest(balance, ["Total Assets"]),
                "liabilities": latest(balance, ["Total Liabilities Net Minority Interest", "Total Liabilities"]),
                "equity": latest(balance, ["Stockholders Equity", "Total Equity Gross Minority Interest"]),
                "debt": latest(balance, ["Total Debt"]),
                "cash": latest(balance, ["Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"]),
                "operating_cash_flow": latest(cashflow, ["Operating Cash Flow"]),
                "free_cash_flow": latest(cashflow, ["Free Cash Flow"]),
            }
            revenue, operating, net, equity, assets, debt = (reported[key] for key in ("revenue", "operating_income", "net_income", "equity", "assets", "debt"))
            calculated = {
                "operating_margin": operating / revenue if operating is not None and revenue not in (None, 0) else None,
                "net_margin": net / revenue if net is not None and revenue not in (None, 0) else None,
                "roe": net / equity if net is not None and equity not in (None, 0) else None,
                "roa": net / assets if net is not None and assets not in (None, 0) else None,
                "debt_to_equity": debt / equity if debt is not None and equity not in (None, 0) else None,
                "pe_ratio": _number(info.get("trailingPE")),
                "price_to_book": _number(info.get("priceToBook")),
            }
            if not any(value is not None for value in reported.values()):
                return _unavailable(requested, "financial_statements", "EMPTY_RESPONSE", "The financial provider returned no reported statement values.")
            return ProviderResult(
                status=DataStatus.LIVE,
                data=FinancialStatement(symbol=requested, currency=info.get("financialCurrency") or info.get("currency"), reported=reported, calculated=calculated),
                provenance=Provenance(source=self.source, symbol=requested, retrieved_at=datetime.now(timezone.utc), exchange=info.get("exchange"), data_type="financial_statements"),
            )
        except Exception as error:
            return _unavailable(requested, "financial_statements", "PROVIDER_REQUEST_FAILED", f"Financial provider request failed: {error}", retryable=True)
