from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, CouncilSession
from app.schemas.council import CouncilRequest, CouncilStage


@pytest.fixture
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def test_council_request_requires_symbol_or_selected_documents():
    with pytest.raises(ValueError):
        CouncilRequest(question="Review recent financial risk")
    assert CouncilRequest(question="Review recent financial risk", symbol=" reliance ").symbol == "RELIANCE"


def test_council_request_rejects_unknown_specialist():
    with pytest.raises(ValueError):
        CouncilRequest(question="Review recent financial risk", symbol="TCS", specialists=["oracle"])


def test_council_persists_partial_report_with_provider_evidence(db_session):
    from app.agents.council import CouncilOrchestrator
    from app.core.config import settings
    from app.providers.models import DataStatus, MarketSnapshot, MarketBar, Provenance, ProviderResult, CompanyProfile, FinancialStatement
    from app.services.container import ServiceContainer

    class FakeLive:
        def market(self, symbol):
            bars = [MarketBar(timestamp=datetime(2026, 1, i + 1, tzinfo=timezone.utc), close=100 + i) for i in range(25)]
            return ProviderResult(status=DataStatus.LIVE, data=MarketSnapshot(symbol=symbol, provider_symbol=symbol, currency="INR", bars=bars, current_price=124), provenance=Provenance(source="controlled-test", symbol=symbol, retrieved_at=datetime.now(timezone.utc), data_type="market"))
        def profile(self, symbol):
            return ProviderResult(status=DataStatus.LIVE, data=CompanyProfile(symbol=symbol, name="Example"), provenance=Provenance(source="controlled-test", symbol=symbol, retrieved_at=datetime.now(timezone.utc), data_type="profile"))
        def financials(self, symbol):
            return ProviderResult(status=DataStatus.LIVE, data=FinancialStatement(symbol=symbol, currency="INR", reported={"revenue": 100.0}, calculated={}), provenance=Provenance(source="controlled-test", symbol=symbol, retrieved_at=datetime.now(timezone.utc), data_type="financials"))
        def news(self, symbol, company_name=None):
            return ProviderResult(status=DataStatus.UNAVAILABLE, data=None)

    container = ServiceContainer(settings=settings, live_data=FakeLive())
    request = CouncilRequest(question="Review the latest financial position", symbol="TCS")
    row = CouncilSession(id="test-council", question=request.question, request_json=request.model_dump(mode="json"), status="CREATED", stage="CREATED")
    db_session.add(row)
    db_session.commit()
    CouncilOrchestrator(container).run(row, db_session, request)
    stored = db_session.get(CouncilSession, row.id)
    assert stored.status == CouncilStage.PARTIAL.value
    assert any(item["source_type"] == "provider" for item in stored.evidence)
    assert len(stored.findings) == 4
    assert stored.report["completion_status"] == "PARTIAL"
    assert stored.debate
    assert any(event["type"] == "session_partial" for event in stored.events)


def test_selected_document_must_be_indexed(db_session):
    from app.agents.council import CouncilOrchestrator
    from app.core.config import settings
    from app.services.container import ServiceContainer
    request = CouncilRequest(question="Check this selected filing", document_ids=["missing-document"])
    row = CouncilSession(id="missing-doc-test", question=request.question, request_json=request.model_dump(mode="json"), status="CREATED", stage="CREATED")
    db_session.add(row)
    db_session.commit()
    CouncilOrchestrator(ServiceContainer(settings=settings, live_data=object())).run(row, db_session, request)
    assert db_session.get(CouncilSession, row.id).status == CouncilStage.FAILED.value
