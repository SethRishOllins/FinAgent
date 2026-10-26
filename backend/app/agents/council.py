from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CouncilSession, Document
from app.rag.embeddings import EmbeddingFailure
from app.rag.vector_store import VectorStoreFailure
from app.schemas.council import AgentFinding, Claim, CouncilReport, CouncilRequest, CouncilStage, DebateMessage, EvidenceReference
from app.services.container import ServiceContainer
from app.services.analytics import technical_summary

ROLES = {"financial": "Financial Analyst", "valuation": "Valuation Analyst", "risk": "Risk Analyst / Contrarian", "evidence": "Evidence Researcher"}


class CouncilOrchestrator:
    """Bounded local evidence workflow. No external generation service receives evidence."""

    def __init__(self, services: ServiceContainer):
        self.services = services

    def _event(self, row: CouncilSession, stage: CouncilStage, name: str, detail: str) -> None:
        now = datetime.now(timezone.utc)
        row.stage = stage.value
        row.events = [*row.events, {"type": name, "stage": stage.value, "detail": detail, "timestamp": now.isoformat()}][-200:]
        row.updated_at = now

    def _collect(self, session: Session, request: CouncilRequest):
        evidence: list[EvidenceReference] = []
        source_status: dict = {}
        gaps: list[str] = []
        if request.symbol:
            live = self.services.live_data
            results = {"market": live.market(request.symbol), "profile": live.profile(request.symbol), "financials": live.financials(request.symbol), "news": live.news(request.symbol)}
            for name, result in results.items():
                source_status[name] = {"status": result.status.value, "source": result.provenance.source if result.provenance else None, "retrieved_at": result.provenance.retrieved_at.isoformat() if result.provenance else None, "data_timestamp": result.provenance.data_timestamp.isoformat() if result.provenance and result.provenance.data_timestamp else None, "error": result.error.message if result.error else None}
                if result.error:
                    gaps.append(f"{name}: {result.error.message}")
            market = results["market"]
            if market.data:
                data = market.data
                metrics = technical_summary([bar.close for bar in data.bars]) if len(data.bars) >= 20 else {"observation_count": len(data.bars)}
                evidence.append(EvidenceReference(id="market-" + str(uuid4()), source_type="provider", title=f"{data.symbol} market history", url=market.provenance.url if market.provenance else None, reporting_period=f"{data.bars[0].timestamp.date()} to {data.bars[-1].timestamp.date()}" if data.bars else None, excerpt=str({"currency": data.currency, "current_price": data.current_price, "change_pct": data.change_pct, "technical_metrics": metrics, "bars": len(data.bars)}), retrieval_metadata={"provider": market.provenance.source if market.provenance else None, "status": market.status.value, "retrieved_at": market.provenance.retrieved_at.isoformat() if market.provenance else None}))
            financials = results["financials"]
            if financials.data:
                item = financials.data
                evidence.append(EvidenceReference(id="financials-" + str(uuid4()), source_type="provider", title=f"{request.symbol} reported financial data", url=financials.provenance.url if financials.provenance else None, reporting_period=financials.provenance.data_timestamp.isoformat() if financials.provenance and financials.provenance.data_timestamp else None, excerpt=str({"currency": item.currency, "reported": item.reported, "calculated": item.calculated}), retrieval_metadata={"provider": financials.provenance.source if financials.provenance else None, "status": financials.status.value, "retrieved_at": financials.provenance.retrieved_at.isoformat() if financials.provenance else None}))
            profile = results["profile"]
            if profile.data:
                evidence.append(EvidenceReference(id="profile-" + str(uuid4()), source_type="provider", title=f"{request.symbol} company profile", url=profile.provenance.url if profile.provenance else None, excerpt=str(profile.data.model_dump(mode="json")), retrieval_metadata={"provider": profile.provenance.source if profile.provenance else None, "status": profile.status.value}))
            news = results["news"]
            if news.data:
                for article in news.data[:8]:
                    evidence.append(EvidenceReference(id="news-" + str(uuid4()), source_type="news", title=article.title, url=article.url, published_at=article.published_at, excerpt=article.summary or article.title, retrieval_metadata={"publisher": article.publisher, "status": news.status.value, "provider": news.provenance.source if news.provenance else None}))
        if request.document_ids:
            if len(set(request.document_ids)) != len(request.document_ids):
                raise ValueError("Duplicate document IDs are not allowed.")
            docs = session.scalars(select(Document).where(Document.id.in_(request.document_ids), Document.status == "indexed")).all()
            if {doc.id for doc in docs} != set(request.document_ids):
                raise ValueError("One or more selected documents do not exist or are not indexed.")
            retrieval = self.services.document_service()
            for doc in docs:
                try:
                    results = retrieval.search(session, request.question, doc.company_symbol, limit=5)
                except (EmbeddingFailure, VectorStoreFailure) as error:
                    gaps.append(f"Document retrieval unavailable: {error}")
                    continue
                for item in results:
                    if item["document_id"] == doc.id:
                        evidence.append(EvidenceReference(id="document-" + str(uuid4()), source_type="uploaded document", title=item["document"], document_id=item["document_id"], page=item.get("page"), section=item.get("section"), excerpt=item["excerpt"], retrieval_metadata={"chunk_id": item.get("chunk_id"), "chunk_index": item.get("chunk_index"), "score": item.get("score"), "retrieval_method": item.get("retrieval_method")}))
        if not evidence:
            gaps.append("No evidence records were available for this question.")
        return evidence, source_status, gaps

    def run(self, row: CouncilSession, session: Session, request: CouncilRequest) -> None:
        try:
            self._event(row, CouncilStage.PLANNING, "planning", "Created bounded specialist tasks from the selected roles and research focus.")
            session.commit()
            self._event(row, CouncilStage.RESEARCHING, "research_started", "Collecting provider results and explicitly selected document passages locally.")
            evidence, source_status, gaps = self._collect(session, request)
            row.evidence = [item.model_dump(mode="json") for item in evidence]
            self._event(row, CouncilStage.INITIAL_FINDINGS, "evidence_collected", f"Collected {len(evidence)} validated source records; {len(gaps)} source limitations recorded.")
            session.commit()
            findings: list[AgentFinding] = []
            for key in request.specialists:
                role = ROLES[key]
                if key == "financial":
                    selected = [item for item in evidence if "financial" in item.id]
                    conclusion = "Reported fields and provider-calculated ratios are shown when present; missing values are not estimated." if selected else "No verified financial statement record was retrieved, so financial condition is undetermined."
                    limitation = ["Provider response may omit fields and reporting-period detail."]
                elif key == "valuation":
                    selected = [item for item in evidence if item.source_type == "provider" and "financial" in item.id]
                    conclusion = "No defensible intrinsic valuation was calculated. Compare only provider-returned valuation fields when present; this project has no supported DCF or peer benchmark inputs." if selected else "Valuation is undetermined because verified valuation and comparable-company inputs were unavailable."
                    limitation = ["No fabricated DCF assumptions or hardcoded peer benchmarks are used."]
                elif key == "risk":
                    selected = [item for item in evidence if item.source_type in {"provider", "news"}]
                    conclusion = "The contrarian review found evidence gaps and will not manufacture an opposing thesis; inspect source limits and adverse reported evidence below." if selected else "Downside risks cannot be assessed from unavailable evidence; no contrary position was invented."
                    limitation = ["No forecast or causal claim is drawn from price history or headlines alone."]
                else:
                    selected = evidence[:]
                    conclusion = f"Retrieved {len(selected)} evidence record(s) from configured providers and explicitly selected indexed documents." if selected else "No relevant provider or document evidence was available."
                    limitation = ["Retrieval does not establish completeness; uploaded passages remain untrusted source content."]
                ids = [item.id for item in selected]
                claims = [Claim(id=str(uuid4()), text=conclusion, kind="interpretation", evidence_ids=ids, status="supported" if ids else "unverified")] if ids else []
                finding = AgentFinding(role=role, status="completed" if selected else "partial", conclusion=conclusion, claims=claims, evidence_ids=ids, limitations=limitation, uncertainties=["LLM-based judgment is not configured; this is an evidence summary, not generated analysis."])
                findings.append(finding)
            row.findings = [item.model_dump(mode="json") for item in findings]
            self._event(row, CouncilStage.DEBATING, "debate_started", "Checking specialist claims against available evidence IDs; no model-generated debate is configured.")
            claims = [claim for finding in findings for claim in finding.claims]
            debate: list[DebateMessage] = []
            if not evidence:
                debate.append(DebateMessage(round_number=1, agent_role="Evidence Judge / Reviewer", message_type="review", argument="No retrieved source supports a substantive conclusion; the council must remain inconclusive.", evidence_ids=[], revision_status="retained"))
            else:
                debate.append(DebateMessage(round_number=1, agent_role="Evidence Judge / Reviewer", message_type="review", argument="Evidence IDs resolve to retrieved records, but this local-only configuration cannot evaluate claim correctness or author a genuine cross-examination. Claims remain qualified and unsupported dimensions are disclosed.", evidence_ids=[item.id for item in evidence], revision_status="qualified"))
            row.debate = [item.model_dump(mode="json") for item in debate]
            self._event(row, CouncilStage.REVIEWING, "review_completed", "Deterministic evidence-reference and availability checks completed; LLM judgment is unavailable.")
            unresolved = [*gaps, "Independent LLM cross-examination and evidence judgment require explicit provider/data-governance configuration."]
            summary = "The available sources do not support a complete financial conclusion. Treat this session as an evidence inventory; no investment recommendation or unsupported valuation was produced."
            report = CouncilReport(research_question=request.question, executive_conclusion=summary, key_findings=[item.conclusion for item in findings], supporting_arguments=[f"{item.title}: {item.excerpt[:500]}" for item in evidence[:10]], opposing_arguments=["No evidence-backed opposing thesis was established by deterministic checks."], material_disagreements=[], unresolved_questions=unresolved, evidence_quality="Limited; source availability and reference integrity checked, factual conclusions not independently model-reviewed.", limitations=[*gaps, "LLM specialist analysis, cross-examination, and semantic evidence judgment are not configured.", "Research output is not financial advice."], sources=evidence, methodology="Configured market, financial, profile, news and explicitly selected document retrieval services were used. Existing deterministic financial/technical calculations were reused. Evidence references were generated from returned source records. One bounded reviewer check disclosed missing semantic review; no LLM or external evidence transmission occurred.", generated_at=datetime.now(timezone.utc), completion_status="PARTIAL")
            row.report = report.model_dump(mode="json")
            row.status = CouncilStage.PARTIAL.value if evidence else CouncilStage.PARTIAL.value
            self._event(row, CouncilStage.FINALIZING, "report_finalized", "Finalized a partial evidence report with explicit capability limits.")
            self._event(row, CouncilStage.PARTIAL, "session_partial", "Evidence collection completed; genuine LLM debate and review are unavailable in this deployment.")
            session.commit()
        except Exception as error:
            session.rollback()
            failed = session.get(CouncilSession, row.id)
            if failed:
                failed.status = CouncilStage.FAILED.value
                failed.failure_reason = str(error)[:2000]
                failed.events = [*failed.events, {"type": "session_failed", "stage": CouncilStage.FAILED.value, "detail": failed.failure_reason, "timestamp": datetime.now(timezone.utc).isoformat()}][-200:]
                session.commit()
