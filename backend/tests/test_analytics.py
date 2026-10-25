import math

import pytest

from app.services.analytics import (
    AnalyticsError,
    backtest_ma_crossover,
    beta,
    forecast_experiment,
    max_drawdown,
    portfolio_risk,
    risk_profile,
    technical_summary,
)


def test_technical_summary_has_expected_metrics():
    result = technical_summary([100 + index for index in range(40)])
    assert result["trend"] == "above"
    assert 0 <= result["rsi14"] <= 100


def test_portfolio_flags_concentration():
    result = portfolio_risk({"RELIANCE": 80, "TCS": 20})
    assert result["risk_flag"] == "high allocation concentration"
    assert result["hhi"] == pytest.approx(0.68)
    assert result["effective_holdings"] == pytest.approx(1.47)


def test_backtest_returns_metrics_and_equity_curve():
    result = backtest_ma_crossover([100 + index for index in range(90)])
    assert result["final_value"] > 0
    assert len(result["equity_curve"]) == 90
    assert result["trade_count"] >= 1


def test_technical_summary_rejects_short_and_non_finite_series():
    with pytest.raises(AnalyticsError):
        technical_summary([100.0] * 19)
    with pytest.raises(AnalyticsError):
        technical_summary([100.0] * 19 + [math.nan])


def test_risk_profile_does_not_invent_beta_without_benchmark():
    result = risk_profile([100 + index for index in range(25)])
    assert result["beta"] is None
    assert result["conventions"].startswith("Historical daily")


def test_beta_is_covariance_based_not_a_volatility_approximation():
    asset = [0.01, 0.02, -0.01, 0.03]
    benchmark = [0.005, 0.01, -0.005, 0.015]
    assert beta(asset, benchmark) == pytest.approx(2.0)
    assert beta(asset, [0.01, 0.01, 0.01, 0.01]) is None


def test_drawdown_uses_running_peak():
    assert max_drawdown([100, 120, 90, 110]) == pytest.approx(-0.25)


def test_portfolio_rejects_short_positions_and_non_finite_weights():
    with pytest.raises(AnalyticsError):
        portfolio_risk({"RELIANCE": 1, "TCS": -1})
    with pytest.raises(AnalyticsError):
        portfolio_risk({"RELIANCE": math.inf})


def test_forecast_uses_walk_forward_evaluation_not_a_fixed_holdout_claim():
    result = forecast_experiment([100 + index for index in range(30)])
    assert result["evaluation_observations"] == 10
    assert result["models"][0]["evaluated_observations"] == 10
    assert result["models"][0]["mae"] == 1.0
    assert result["models"][0]["directional_accuracy"] == 0.0


def test_backtest_has_no_future_signal_on_first_return_and_costs_reduce_value():
    prices = [100.0] * 20 + [200.0, 100.0, 100.0, 100.0]
    no_cost = backtest_ma_crossover(prices, transaction_cost=0)
    with_cost = backtest_ma_crossover(prices, transaction_cost=0.01)
    assert no_cost["equity_curve"][1] == 100000.0
    assert with_cost["final_value"] <= no_cost["final_value"]
