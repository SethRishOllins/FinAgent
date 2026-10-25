# Financial Methodology

## Data modes

`DATA_MODE=live` uses configured external providers and returns `LIVE`, `CACHED`, or `UNAVAILABLE`. `DATA_MODE=demo` uses deterministic synthetic records labelled `DEMO`; it is for offline demonstration only and never a fallback from live mode.

## Return conventions

Price calculations use daily simple returns: `(P_t / P_(t-1)) - 1`. Annualization uses 252 trading days. The default annual risk-free rate is 6.5%.

## Indicators and risk metrics

- SMA: trailing arithmetic mean.
- EMA: recursive moving average with `alpha = 2 / (window + 1)`.
- RSI: Wilder-smoothed 14-period RSI. A no-loss rising period has RSI 100; a flat period has RSI 50.
- Maximum drawdown: minimum `price / running_peak - 1`.
- Sharpe: annualized excess simple return divided by annualized sample volatility.
- Sortino: annualized excess return divided by annualized downside deviation below the daily risk-free rate.
- Historical VaR/CVaR: empirical 5% lower-tail loss and tail-loss average.
- Beta: covariance of aligned asset and benchmark returns divided by benchmark variance. It is unavailable without aligned variable benchmark returns.

## Portfolio concentration

Finite non-negative holding values are normalized to weights. HHI is the sum of squared weights; effective holdings is `1 / HHI`. This is allocation concentration, not a declaration that the portfolio is safe or unsafe.

## Forecast experiment

Naive last-observation and linear-trend price baselines are evaluated with chronological one-session rolling-origin splits. Each prediction uses only prices observed before the actual value. MAE, RMSE, evaluated sample count, and directional accuracy are measured from those held-out predictions.

## Backtest

The implemented strategy is long-only and either fully invested or in cash. A signal observed at close is applied only to the following session. Configurable transaction costs are charged on every position change. Historical results are not forecasts or evidence of future profitability.
