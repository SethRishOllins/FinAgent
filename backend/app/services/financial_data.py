from dataclasses import dataclass


@dataclass(frozen=True)
class CompanyFundamentals:
    symbol: str
    company: str
    sector: str
    revenue: float
    revenue_growth: float
    ebitda_margin: float
    net_margin: float
    eps: float
    roe: float
    roce: float
    debt_to_equity: float
    current_ratio: float
    pe: float
    pb: float
    ev_to_ebitda: float
    free_cash_flow: float
    market_cap: float


FUNDAMENTALS = {
    "RELIANCE": CompanyFundamentals("RELIANCE", "Reliance Industries Ltd.", "Energy & Conglomerate", 1008.0, 6.2, 16.4, 9.1, 92.8, 8.4, 9.7, 0.42, 1.14, 24.7, 2.1, 12.6, 111.2, 1980.0),
    "TCS": CompanyFundamentals("TCS", "Tata Consultancy Services Ltd.", "Information Technology", 255.3, 7.4, 25.1, 19.3, 126.7, 52.1, 68.0, 0.09, 2.45, 29.8, 14.8, 21.3, 45.9, 1410.0),
    "INFY": CompanyFundamentals("INFY", "Infosys Ltd.", "Information Technology", 162.9, 4.8, 23.5, 17.1, 63.2, 29.7, 37.1, 0.12, 2.18, 25.4, 7.4, 17.8, 31.6, 670.0),
    "HDFCBANK": CompanyFundamentals("HDFCBANK", "HDFC Bank Ltd.", "Financial Services", 309.0, 11.6, 0.0, 0.0, 89.5, 15.2, 0.0, 1.19, 0.0, 19.2, 2.7, 0.0, 0.0, 1260.0),
}


def fundamentals(symbol: str) -> CompanyFundamentals:
    key = symbol.upper().replace(".NS", "")
    if key not in FUNDAMENTALS:
        raise ValueError(f"No fundamentals are available for {symbol}.")
    return FUNDAMENTALS[key]


def peer_table(symbols: list[str]) -> list[dict]:
    return [fundamentals(symbol).__dict__ for symbol in symbols]


def sample_news(symbol: str) -> list[dict]:
    company = fundamentals(symbol).company
    return [
        {"headline": f"{company}: operating update highlights execution priorities", "company": symbol.upper(), "sentiment": "neutral", "event": "Company update", "materiality": "medium", "confidence": 0.71, "source": "Offline research sample", "timestamp": "Demo dataset"},
        {"headline": f"Sector context reviewed for {company}", "company": symbol.upper(), "sentiment": "neutral", "event": "Sector context", "materiality": "low", "confidence": 0.64, "source": "Offline research sample", "timestamp": "Demo dataset"},
    ]
