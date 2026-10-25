from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.models import Base, DataSourceMetadata, Document
from app.db.repository import list_reports, save_provenance, save_research
from app.main import health
from app.providers.models import DataStatus, MarketBar, MarketSnapshot, ProviderResult, Provenance
from app.providers.newsapi_provider import NewsApiProvider
from app.providers.demo_provider import DemoProvider
from app.providers.registry import ProviderRegistry
from app.providers.yfinance_provider import YahooFinanceProvider
from app.core.config import Settings
from app.providers.yfinance_provider import provider_symbol
from app.rag.chunking import chunk_document
from app.rag.parser import DocumentParseError, parse_document
from app.rag.embeddings import EmbeddingFailure, embedding_error_message
from app.rag.service import DocumentService
from app.rag.vector_store import VectorMatch, VectorStore
from app.services.cache import RedisJsonCache


class FakeRedis:
    def __init__(self):
        self.values = {}

    def setex(self, key, ttl, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)

    def ping(self):
        return True


class FakeEmbeddings:
    dimensions = 3

    def embed(self, texts):
        return [[float(len(text)), 0.0, 1.0] for text in texts]


class FakeVectors(VectorStore):
    def __init__(self):
        self.points = []

    def upsert(self, points):
        self.points.extend(points)

    def search(self, vector, limit, company=None):
        return [VectorMatch(vector_id=point[0], score=0.91, payload=point[2]) for point in self.points if not company or point[2]["company"] == company.upper()][:limit]

    def delete_document(self, document_id):
        self.points = [point for point in self.points if point[2].get("document_id") != document_id]


def memory_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_news_provider_reports_missing_credentials_without_sample_articles():
    response = NewsApiProvider(api_key=None).news("RELIANCE")
    assert response.status == DataStatus.UNAVAILABLE
    assert response.data is None
    assert response.error.code == "PROVIDER_NOT_CONFIGURED"


def test_indian_equity_symbols_are_normalized_at_the_provider_boundary():
    assert provider_symbol("reliance") == "RELIANCE.NS"
    assert provider_symbol("NIFTY") == "^NSEI"


def test_market_snapshot_keeps_history_when_yahoo_fast_info_lacks_trading_period():
    class Timestamp:
        def to_pydatetime(self):
            return datetime(2026, 10, 25, tzinfo=timezone.utc)

    class History:
        empty = False
        def iterrows(self):
            return iter([(Timestamp(), {"Open": 99, "High": 102, "Low": 98, "Close": 101, "Volume": 1000})])

    class Ticker:
        def history(self, **kwargs):
            return History()

        @property
        def fast_info(self):
            raise KeyError("currentTradingPeriod")

    provider = YahooFinanceProvider()
    provider._ticker = lambda symbol: Ticker()
    result = provider.snapshot("RELIANCE")
    assert result.status == DataStatus.LIVE
    assert result.data.current_price == 101
    assert result.data.bars[-1].close == 101


def test_cache_marks_verified_cached_result_explicitly():
    cache = RedisJsonCache(None)
    cache.client = FakeRedis()
    result = ProviderResult[MarketSnapshot](
        status=DataStatus.LIVE,
        data=MarketSnapshot(symbol="RELIANCE", provider_symbol="RELIANCE.NS", bars=[MarketBar(timestamp=datetime.now(timezone.utc), close=100.0)]),
        provenance=Provenance(source="test", symbol="RELIANCE", retrieved_at=datetime.now(timezone.utc), data_type="market_history"),
    )
    cache.set("market", result, 60)
    cached = cache.get("market", MarketSnapshot)
    assert cached is not None
    assert cached.status == DataStatus.CACHED
    assert cached.data.bars[0].close == 100.0


def test_document_ingestion_persists_chunks_and_returns_citations():
    session = memory_session()
    vectors = FakeVectors()
    service = DocumentService(embeddings=FakeEmbeddings(), vectors=vectors)
    document = service.ingest(session, "annual-report.md", b"# Revenue\nRevenue improved because costs declined.\n# Risks\nLiquidity risk remains monitored.", "RELIANCE", "text/markdown")
    assert document.status == "indexed"
    results = service.search(session, "What happened to revenue?", "RELIANCE")
    assert results[0]["document"] == "annual-report.md"
    assert results[0]["source"] == "uploaded document"
    assert results[0]["start_offset"] is not None
    assert results[0]["chunk_id"]


def test_failed_embedding_keeps_a_persistent_failed_document_record():
    class UnavailableEmbeddings:
        dimensions = 3
        def embed(self, texts):
            raise EmbeddingFailure("embedding unavailable")

    session = memory_session()
    service = DocumentService(embeddings=UnavailableEmbeddings(), vectors=FakeVectors())
    try:
        service.ingest(session, "report.txt", b"Revenue for the financial year was 42 crore rupees.", None, "text/plain")
        assert False, "expected embedding failure"
    except EmbeddingFailure:
        pass
    document = session.query(Document).one()
    assert document.status == "failed"
    assert "embedding unavailable" in document.ingestion_error


def test_embedding_failures_are_actionable_without_leaking_sdk_details():
    class RateLimitError(Exception):
        status_code = 429
    assert "quota" in embedding_error_message(RateLimitError("sensitive provider detail"))
    assert "sensitive provider detail" not in embedding_error_message(RateLimitError("sensitive provider detail"))

    class AuthenticationError(Exception):
        status_code = 401
    assert "OPENAI_API_KEY" in embedding_error_message(AuthenticationError("secret"))


def test_csv_parser_keeps_financial_metric_and_period_together():
    parsed = parse_document("metrics.csv", b"Metric,Period,Value,Unit\nRevenue,FY2025,42,INR crore\n")
    assert "Metric: Revenue" in parsed.pages[0].text
    assert "Period: FY2025" in parsed.pages[0].text
    assert "Value: 42" in parsed.pages[0].text


def test_parser_rejects_empty_binary_unsupported_and_short_invalid_documents():
    for name, content in [("notes.txt", b""), ("image.bin", b"some random bytes"), ("notes.txt", b"\x00\xff\xfe")]:
        try:
            parse_document(name, content)
            assert False, "invalid document accepted"
        except DocumentParseError:
            pass


def test_pdf_upload_path_does_not_decode_bytes_as_utf8():
    try:
        parse_document("report.pdf", b"%PDF-invalid\xff")
        assert False, "malformed PDF accepted"
    except DocumentParseError as error:
        assert "PDF" in str(error)


def test_chunking_is_deterministic_and_preserves_page_and_offsets():
    from app.rag.parser import ParsedDocument, ParsedPage
    document = ParsedDocument("sample", "text/plain", [ParsedPage("one two three four five six", 3, "Results")], {})
    first = chunk_document(document, max_words=3, overlap_words=1)
    second = chunk_document(document, max_words=3, overlap_words=1)
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert first[0].page_number == 3 and first[0].section == "Results"
    assert first[0].start_offset == 0 and first[0].end_offset == len("one two three")
    assert first[1].content.startswith("three")


def test_empty_pdf_reports_ocr_requirement():
    import io
    from pypdf import PdfWriter
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(buffer)
    try:
        parse_document("scan.pdf", buffer.getvalue())
        assert False, "scanned-like empty PDF accepted"
    except DocumentParseError as error:
        assert "OCR" in str(error)


def test_research_report_is_durable_in_database():
    session = memory_session()
    save_research(session, {"run_id": "run-1", "symbol": "RELIANCE", "summary": "Evidence-scoped summary", "findings": [], "warnings": ["Review source"], "activity": [], "provenance": {}}, "Test question")
    session.commit()
    assert list_reports(session)[0]["run_id"] == "run-1"


def test_json_provenance_is_coerced_to_database_timestamps():
    session = memory_session()
    save_provenance(session, {"symbol": "RELIANCE", "source": "test", "data_type": "market_history", "status": "LIVE", "retrieved_at": "2026-10-07T00:00:00+00:00", "data_timestamp": "2026-10-06T00:00:00+00:00", "payload": {"status": "LIVE"}})
    session.commit()


def test_datetime_nested_in_provenance_json_is_encoded_before_postgres_write():
    session = memory_session()
    retrieved = datetime.now(timezone.utc)
    save_provenance(session, {"symbol": "RELIANCE", "source": "test", "data_type": "research_input", "status": "LIVE", "retrieved_at": retrieved, "data_timestamp": None, "payload": {"retrieved_at": retrieved}})
    session.commit()
    record = session.query(DataSourceMetadata).one()
    assert record.payload["retrieved_at"] == retrieved.isoformat()


def test_health_contract_exposes_data_mode():
    from app.services.container import build_container
    assert health(build_container())["data_mode"] in {"live", "demo"}


def test_demo_provider_is_explicitly_labelled_and_deterministic():
    provider = DemoProvider()
    first = provider.snapshot("reliance")
    second = provider.snapshot("RELIANCE")
    assert first.status == DataStatus.DEMO
    assert first.data is not None
    assert [bar.close for bar in first.data.bars] == [bar.close for bar in second.data.bars]
    assert "demonstration" in first.provenance.source.lower()


def test_registry_never_selects_demo_without_explicit_mode():
    demo_registry = ProviderRegistry(Settings(data_mode="demo"))
    live_registry = ProviderRegistry(Settings(data_mode="live"))
    assert isinstance(demo_registry.market, DemoProvider)
    assert not isinstance(live_registry.market, DemoProvider)
