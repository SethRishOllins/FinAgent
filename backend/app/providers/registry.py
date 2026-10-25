from app.core.config import Settings
from app.providers.demo_provider import DemoProvider
from app.providers.newsapi_provider import NewsApiProvider
from app.providers.yfinance_provider import YahooFinanceProvider


class ProviderRegistry:
    """Application-level provider composition; business services depend on contracts."""

    def __init__(self, settings: Settings):
        if settings.data_mode.lower() == "demo":
            demo = DemoProvider()
            self.market = demo
            self.financials = demo
            self.profiles = demo
            self.news = demo
        else:
            self.market = YahooFinanceProvider()
            self.financials = YahooFinanceProvider()
            self.profiles = YahooFinanceProvider()
            self.news = NewsApiProvider(settings.newsapi_key)
