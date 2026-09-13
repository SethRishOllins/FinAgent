from app.services.analytics import portfolio_risk, technical_summary


def test_technical_summary_has_expected_metrics():
    result = technical_summary([100 + index for index in range(40)])
    assert result["trend"] == "above"
    assert 0 <= result["rsi14"] <= 100


def test_portfolio_flags_concentration():
    result = portfolio_risk({"RELIANCE": 80, "TCS": 20})
    assert result["risk_flag"] == "high concentration"
