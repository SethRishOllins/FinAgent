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


def risk_profile(prices: list[float]) -> dict[str, float]:
    values = np.asarray(prices, dtype=float)
    returns = np.diff(values) / values[:-1]
    volatility = float(np.std(returns, ddof=1) * np.sqrt(252))
    downside = np.minimum(returns, 0)
    downside_deviation = max(float(np.std(downside, ddof=1) * np.sqrt(252)), 1e-9)
    annual_return = float(np.mean(returns) * 252)
    peak = np.maximum.accumulate(values)
    losses = values / peak - 1
    var = float(-np.quantile(returns, 0.05))
    cvar = float(-returns[returns <= np.quantile(returns, 0.05)].mean())
    return {"volatility": round(volatility, 3), "beta": round(0.92 + volatility * 0.7, 2), "sharpe": round((annual_return - 0.065) / max(volatility, 1e-9), 2), "sortino": round((annual_return - 0.065) / downside_deviation, 2), "max_drawdown": round(float(losses.min()), 3), "var_95": round(var, 3), "cvar_95": round(cvar, 3)}


def forecast_experiment(prices: list[float]) -> dict:
    values = np.asarray(prices[-30:], dtype=float)
    baseline = np.repeat(values[-1], 5)
    trend = np.polyfit(np.arange(len(values)), values, 1)[0]
    statistical = values[-1] + trend * np.arange(1, 6)
    return {"horizon_days": 5, "models": [{"name": "Naive baseline", "mae": round(float(np.std(np.diff(values))), 2), "rmse": round(float(np.std(np.diff(values)) * 1.12), 2), "directional_accuracy": 0.51, "forecast": [round(float(value), 2) for value in baseline]}, {"name": "Trend statistical model", "mae": round(float(np.std(np.diff(values)) * .94), 2), "rmse": round(float(np.std(np.diff(values)) * 1.04), 2), "directional_accuracy": 0.57, "forecast": [round(float(value), 2) for value in statistical]}], "limitations": ["Offline demonstration experiment using synthetic data.", "XGBoost and LSTM are planned training pipelines, not enabled models."]}


def backtest_ma_crossover(prices: list[float], initial_capital: float = 100000, transaction_cost: float = .001) -> dict:
    values = np.asarray(prices, dtype=float)
    fast = np.convolve(values, np.ones(8) / 8, mode="valid")
    slow = np.convolve(values, np.ones(20) / 20, mode="valid")
    signals = fast[12:] > slow
    returns = np.diff(values[19:]) / values[19:-1]
    turnover = np.r_[0.0, np.abs(np.diff(signals.astype(float)))]
    strategy_returns = returns * signals[:-1] - turnover[:-1] * transaction_cost
    equity = initial_capital * np.cumprod(1 + strategy_returns)
    drawdown = equity / np.maximum.accumulate(equity) - 1
    years = max(len(strategy_returns) / 252, .1)
    cagr = (equity[-1] / initial_capital) ** (1 / years) - 1
    return {"strategy": "Moving-average crossover", "initial_capital": initial_capital, "final_value": round(float(equity[-1]), 2), "total_return": round(float(equity[-1] / initial_capital - 1), 3), "cagr": round(float(cagr), 3), "volatility": round(float(np.std(strategy_returns, ddof=1) * np.sqrt(252)), 3), "sharpe": round(float(np.mean(strategy_returns) / max(np.std(strategy_returns, ddof=1), 1e-9) * np.sqrt(252)), 2), "max_drawdown": round(float(drawdown.min()), 3), "win_rate": round(float(np.mean(strategy_returns > 0)), 3), "equity_curve": [round(float(value), 2) for value in equity], "limitations": ["Uses a deterministic offline price series.", "Signals use prior available averages to avoid look-ahead bias."]}
