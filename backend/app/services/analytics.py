from __future__ import annotations

from collections.abc import Sequence
from math import sqrt

import numpy as np


TRADING_DAYS = 252


class AnalyticsError(ValueError):
    """Raised when a metric cannot be calculated from the supplied observations."""


def _prices(prices: Sequence[float], minimum: int = 2) -> np.ndarray:
    values = np.asarray(prices, dtype=float)
    if values.ndim != 1 or len(values) < minimum:
        raise AnalyticsError(f"At least {minimum} price observations are required.")
    if not np.isfinite(values).all() or (values <= 0).any():
        raise AnalyticsError("Prices must be finite, positive observations.")
    return values


def _returns(prices: Sequence[float], minimum: int = 2) -> np.ndarray:
    values = _prices(prices, minimum + 1)
    return np.diff(values) / values[:-1]


def _rounded(value: float | None, digits: int = 4) -> float | None:
    return round(float(value), digits) if value is not None and np.isfinite(value) else None


def simple_moving_average(prices: Sequence[float], window: int) -> np.ndarray:
    if window < 1:
        raise AnalyticsError("Moving-average window must be positive.")
    values = _prices(prices, window)
    return np.convolve(values, np.ones(window) / window, mode="valid")


def exponential_moving_average(prices: Sequence[float], window: int) -> np.ndarray:
    if window < 1:
        raise AnalyticsError("Moving-average window must be positive.")
    values = _prices(prices, window)
    alpha = 2 / (window + 1)
    output = np.empty(len(values), dtype=float)
    output[0] = values[0]
    for index in range(1, len(values)):
        output[index] = alpha * values[index] + (1 - alpha) * output[index - 1]
    return output


def rsi_wilder(prices: Sequence[float], window: int = 14) -> float | None:
    values = _prices(prices, window + 1)
    changes = np.diff(values)
    average_gain = float(np.maximum(changes[:window], 0).mean())
    average_loss = float(np.maximum(-changes[:window], 0).mean())
    for change in changes[window:]:
        average_gain = ((window - 1) * average_gain + max(float(change), 0.0)) / window
        average_loss = ((window - 1) * average_loss + max(-float(change), 0.0)) / window
    if average_loss == 0:
        return 100.0 if average_gain > 0 else 50.0
    return 100 - (100 / (1 + average_gain / average_loss))


def max_drawdown(prices: Sequence[float]) -> float:
    values = _prices(prices)
    running_peak = np.maximum.accumulate(values)
    return float(np.min(values / running_peak - 1))


def historical_var(returns: Sequence[float], confidence: float = 0.95) -> float | None:
    values = np.asarray(returns, dtype=float)
    if len(values) < 2 or not np.isfinite(values).all() or not 0 < confidence < 1:
        return None
    return float(-np.quantile(values, 1 - confidence))


def historical_cvar(returns: Sequence[float], confidence: float = 0.95) -> float | None:
    threshold = historical_var(returns, confidence)
    if threshold is None:
        return None
    values = np.asarray(returns, dtype=float)
    tail = values[values <= -threshold]
    return float(-tail.mean()) if len(tail) else None


def beta(asset_returns: Sequence[float], benchmark_returns: Sequence[float]) -> float | None:
    asset = np.asarray(asset_returns, dtype=float)
    benchmark = np.asarray(benchmark_returns, dtype=float)
    if len(asset) != len(benchmark) or len(asset) < 2:
        return None
    mask = np.isfinite(asset) & np.isfinite(benchmark)
    asset, benchmark = asset[mask], benchmark[mask]
    variance = float(np.var(benchmark, ddof=1)) if len(benchmark) > 1 else 0.0
    return float(np.cov(asset, benchmark, ddof=1)[0, 1] / variance) if variance > 0 else None


def technical_summary(prices: Sequence[float]) -> dict[str, float | str | None]:
    values = _prices(prices, 20)
    returns = _returns(values)
    ma20 = float(simple_moving_average(values, 20)[-1])
    volatility = float(np.std(returns, ddof=1) * sqrt(TRADING_DAYS)) if len(returns) > 1 else None
    return {
        "ma20": _rounded(ma20, 2),
        "ema20": _rounded(float(exponential_moving_average(values, 20)[-1]), 2),
        "rsi14": _rounded(rsi_wilder(values, 14), 1),
        "annual_volatility": _rounded(volatility),
        "max_drawdown": _rounded(max_drawdown(values)),
        "trend": "above" if values[-1] >= ma20 else "below",
        "conventions": "Daily simple returns; 252 trading-day annualization; Wilder RSI(14).",
    }


def portfolio_risk(holdings: dict[str, float]) -> dict[str, float | str | int]:
    if not holdings:
        raise AnalyticsError("At least one holding is required.")
    values = np.asarray(list(holdings.values()), dtype=float)
    if not np.isfinite(values).all() or (values < 0).any():
        raise AnalyticsError("Holdings must be finite, non-negative values; short positions are not supported.")
    total = float(values.sum())
    if total <= 0:
        raise AnalyticsError("Portfolio allocations must total more than zero.")
    weights = values / total
    hhi = float(np.sum(weights**2))
    largest = float(weights.max())
    return {
        "total_weight": _rounded(float(weights.sum())),
        "largest_position": _rounded(largest),
        "concentration_index": _rounded(hhi),
        "hhi": _rounded(hhi),
        "effective_holdings": _rounded(1 / hhi, 2),
        "holding_count": int(len(weights)),
        "risk_flag": "high allocation concentration" if largest > 0.35 else "moderate allocation concentration" if largest > 0.20 else "lower allocation concentration",
        "assumptions": "Long-only non-negative holding values normalized to 100%. This measures allocation concentration, not complete financial risk.",
    }


def risk_profile(prices: Sequence[float], benchmark_prices: Sequence[float] | None = None, risk_free_rate: float = 0.065) -> dict[str, float | None | str]:
    values = _prices(prices, 3)
    returns = _returns(values)
    annual_return = float(np.mean(returns) * TRADING_DAYS)
    volatility = float(np.std(returns, ddof=1) * sqrt(TRADING_DAYS)) if len(returns) > 1 else None
    downside = np.minimum(returns - risk_free_rate / TRADING_DAYS, 0)
    downside_deviation = float(np.sqrt(np.mean(downside**2)) * sqrt(TRADING_DAYS)) if len(downside) else None
    benchmark_returns = _returns(benchmark_prices) if benchmark_prices is not None else None
    aligned_beta = beta(returns[-len(benchmark_returns):], benchmark_returns) if benchmark_returns is not None else None
    return {
        "volatility": _rounded(volatility),
        "beta": _rounded(aligned_beta),
        "sharpe": _rounded((annual_return - risk_free_rate) / volatility if volatility and volatility > 0 else None),
        "sortino": _rounded((annual_return - risk_free_rate) / downside_deviation if downside_deviation and downside_deviation > 0 else None),
        "max_drawdown": _rounded(max_drawdown(values)),
        "var_95": _rounded(historical_var(returns)),
        "cvar_95": _rounded(historical_cvar(returns)),
        "conventions": "Historical daily simple returns, 252 trading-day annualization, and 6.5% annual risk-free rate. Beta requires aligned benchmark returns.",
    }


def forecast_experiment(prices: Sequence[float], horizon: int = 1, min_train_size: int = 20) -> dict:
    """Evaluate simple price-level baselines with chronological rolling-origin splits."""
    if horizon != 1:
        raise AnalyticsError("Only one-session walk-forward evaluation is implemented.")
    values = _prices(prices, min_train_size + horizon + 1)
    predictions: dict[str, list[float]] = {"Naive last-observation baseline": [], "Linear trend baseline": []}
    actual: list[float] = []
    previous: list[float] = []
    for endpoint in range(min_train_size, len(values)):
        training = values[:endpoint]
        predictions["Naive last-observation baseline"].append(float(training[-1]))
        slope, intercept = np.polyfit(np.arange(len(training)), training, 1)
        predictions["Linear trend baseline"].append(float(intercept + slope * len(training)))
        actual.append(float(values[endpoint]))
        previous.append(float(training[-1]))

    def evaluate(name: str, predicted: list[float]) -> dict:
        forecast, observed, prior = np.asarray(predicted), np.asarray(actual), np.asarray(previous)
        changes, forecast_changes = np.sign(observed - prior), np.sign(forecast - prior)
        meaningful = (changes != 0) | (forecast_changes != 0)
        return {
            "name": name,
            "mae": _rounded(float(np.mean(np.abs(observed - forecast)))),
            "rmse": _rounded(float(np.sqrt(np.mean((observed - forecast) ** 2)))),
            "directional_accuracy": _rounded(float(np.mean(changes[meaningful] == forecast_changes[meaningful])) if meaningful.any() else None),
            "evaluated_observations": int(len(observed)),
        }

    slope, intercept = np.polyfit(np.arange(len(values)), values, 1)
    models = [evaluate(name, prediction) for name, prediction in predictions.items()]
    models[0]["forecast"] = [round(float(values[-1]), 4)]
    models[1]["forecast"] = [round(float(intercept + slope * len(values)), 4)]
    return {
        "horizon_days": horizon,
        "evaluation": "Chronological one-session rolling-origin evaluation. Every prediction uses only prior closes.",
        "evaluation_observations": len(actual),
        "training_observations_at_first_evaluation": min_train_size,
        "models": models,
        "limitations": ["Baseline forecasts of price levels are not investment recommendations.", "Metrics are measured only on the supplied historical close series."],
    }


def backtest_ma_crossover(prices: Sequence[float], initial_capital: float = 100000, transaction_cost: float = 0.001, fast_window: int = 8, slow_window: int = 20, risk_free_rate: float = 0.065) -> dict:
    values = _prices(prices, slow_window + 2)
    if initial_capital <= 0 or not np.isfinite(initial_capital):
        raise AnalyticsError("Initial capital must be a positive finite number.")
    if not 0 <= transaction_cost < 1:
        raise AnalyticsError("Transaction cost must be between zero and one.")
    if not 1 <= fast_window < slow_window:
        raise AnalyticsError("Fast window must be positive and shorter than slow window.")
    fast, slow = simple_moving_average(values, fast_window), simple_moving_average(values, slow_window)
    signal = np.zeros(len(values), dtype=float)
    signal[slow_window - 1:] = (fast[slow_window - fast_window:] > slow).astype(float)
    # Signals are observed at close and affect only the following session's return.
    position = np.r_[0.0, signal[:-1]]
    asset_returns = np.r_[0.0, np.diff(values) / values[:-1]]
    turnover = np.abs(np.diff(position, prepend=0.0))
    costs = turnover * transaction_cost
    strategy_returns = position * asset_returns - costs
    equity = initial_capital * np.cumprod(1 + strategy_returns)
    benchmark_equity = initial_capital * np.cumprod(1 + asset_returns)
    active_returns = strategy_returns[1:]
    years = len(active_returns) / TRADING_DAYS
    volatility = float(np.std(active_returns, ddof=1) * sqrt(TRADING_DAYS)) if len(active_returns) > 1 else None
    downside = np.minimum(active_returns - risk_free_rate / TRADING_DAYS, 0)
    downside_deviation = float(np.sqrt(np.mean(downside**2)) * sqrt(TRADING_DAYS)) if len(downside) else None
    return {
        "strategy": "Long-only moving-average crossover",
        "rules": f"Hold when {fast_window}-session SMA is above {slow_window}-session SMA at close; apply the signal to the following session.",
        "initial_capital": round(float(initial_capital), 2),
        "final_value": round(float(equity[-1]), 2),
        "total_return": _rounded(float(equity[-1] / initial_capital - 1)),
        "cagr": _rounded(float((equity[-1] / initial_capital) ** (1 / years) - 1) if years > 0 else None),
        "volatility": _rounded(volatility),
        "sharpe": _rounded((float(np.mean(active_returns)) * TRADING_DAYS - risk_free_rate) / volatility if volatility and volatility > 0 else None),
        "sortino": _rounded((float(np.mean(active_returns)) * TRADING_DAYS - risk_free_rate) / downside_deviation if downside_deviation and downside_deviation > 0 else None),
        "max_drawdown": _rounded(max_drawdown(equity)),
        "win_rate": _rounded(float(np.mean(active_returns > 0)) if len(active_returns) else None),
        "trade_count": int(np.count_nonzero(turnover)),
        "turnover": _rounded(float(turnover.sum())),
        "estimated_costs": round(float(initial_capital * costs.sum()), 2),
        "transaction_cost_rate": transaction_cost,
        "benchmark_total_return": _rounded(float(benchmark_equity[-1] / initial_capital - 1)),
        "equity_curve": [round(float(value), 2) for value in equity],
        "benchmark_equity_curve": [round(float(value), 2) for value in benchmark_equity],
        "limitations": ["Long-only fully invested-or-cash strategy with transaction costs at each position change.", "Historical results do not establish future performance."],
    }
