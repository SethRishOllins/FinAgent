from dataclasses import dataclass
from datetime import datetime, timezone
import numpy as np


@dataclass(frozen=True)
class MarketSnapshot:
    symbol: str
    company: str
    price: float
    change_pct: float
    prices: list[float]
    as_of: str
    source: str


class DemoMarketDataProvider:
    """Reproducible offline provider; replace through this interface for production."""
    companies = {"RELIANCE": "Reliance Industries Ltd.", "TCS": "Tata Consultancy Services Ltd.", "INFY": "Infosys Ltd.", "HDFCBANK": "HDFC Bank Ltd."}

    def search(self, query: str) -> list[dict[str, str]]:
        query = query.upper()
        return [{"symbol": key, "name": value, "exchange": "NSE"} for key, value in self.companies.items() if query in key or query in value.upper()]

    def snapshot(self, symbol: str) -> MarketSnapshot:
        normalized = symbol.upper().replace(".NS", "")
        if normalized not in self.companies:
            raise ValueError(f"Unknown demo symbol: {symbol}")
        seed = sum(map(ord, normalized)); rng = np.random.default_rng(seed)
        prices = (1000 + (seed % 1300)) * np.cumprod(1 + rng.normal(0.0007, 0.016, 90))
        return MarketSnapshot(normalized, self.companies[normalized], round(float(prices[-1]), 2), round(float((prices[-1] / prices[-2] - 1) * 100), 2), [round(float(x), 2) for x in prices], datetime.now(timezone.utc).isoformat(), "offline-demo-provider")


market_data = DemoMarketDataProvider()
