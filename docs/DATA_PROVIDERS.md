# Data Providers

## Yahoo Finance via yfinance

The provider maps `RELIANCE` to `RELIANCE.NS`, `NIFTY` to `^NSEI`, and normalizes historical bars, profile metadata, and selected financial fields. Each result identifies provider, source timestamp, exchange/currency where present, and `LIVE` or `UNAVAILABLE` status.

Availability, refresh cadence, coverage, and permitted use must be verified in the deployment environment. FinAgent must not describe it as real-time NSE data without a provider agreement that supports that claim.

## NewsAPI

NewsAPI is used only when `NEWSAPI_KEY` is configured. Articles retain their title, publisher, URL, and publication timestamp. Missing credentials or provider failures return an explicit unavailable status and never generated headlines.

## Demo provider

Set `DATA_MODE=demo` for deterministic offline demonstrations. Every value carries `DEMO` status and a synthetic-provider identity. These values are never current market information.

## Redis cache

Redis is optional. Only verified `LIVE` provider results are cached; cache hits become `CACHED`. Cache failure is bypassed instead of misrepresented as live data.
