import numpy as np


def technical_summary(prices: list[float]) -> dict[str, float | str]:
    values = np.asarray(prices, dtype=float); returns = np.diff(values) / values[:-1]
    ma20 = values[-20:].mean(); delta = np.diff(values)
    gains, losses = np.maximum(delta, 0), -np.minimum(delta, 0)
    rs = gains[-14:].mean() / max(losses[-14:].mean(), 1e-9)
    peak = np.maximum.accumulate(values)
    return {"ma20": round(float(ma20), 2), "rsi14": round(float(100 - 100 / (1 + rs)), 1), "annual_volatility": round(float(np.std(returns, ddof=1) * np.sqrt(252)), 3), "max_drawdown": round(float(np.min(values / peak - 1)), 3), "trend": "above" if values[-1] >= ma20 else "below"}


def portfolio_risk(holdings: dict[str, float]) -> dict[str, float | str]:
    total = sum(holdings.values())
    if total <= 0:
        raise ValueError("Portfolio allocations must total more than zero.")
    weights = np.array(list(holdings.values()), dtype=float) / total
    return {"total_weight": round(float(weights.sum()), 4), "largest_position": round(float(weights.max()), 4), "concentration_index": round(float(np.sum(weights**2)), 4), "risk_flag": "high concentration" if weights.max() > 0.35 else "diversified relative to configured threshold"}
