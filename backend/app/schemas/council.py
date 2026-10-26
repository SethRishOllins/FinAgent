from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, Field, model_validator


class CouncilStage(StrEnum):
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    RESEARCHING = "RESEARCHING"
    INITIAL_FINDINGS = "INITIAL_FINDINGS"
    DEBATING = "DEBATING"
    REVIEWING = "REVIEWING"
    REVISION = "REVISION"
    FINALIZING = "FINALIZING"
    COMPLETED = "COMPLETED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class EvidenceReference(BaseModel):
    id: str
    source_type: str
    title: str
    url: str | None = None
    document_id: str | None = None
    page: int | None = None
    section: str | None = None
    published_at: datetime | None = None
    reporting_period: str | None = None
    excerpt: str
    retrieval_metadata: dict = Field(default_factory=dict)
    verification_status: str = "retrieved"


class Claim(BaseModel):
    id: str
    text: str
    kind: str = "interpretation"
    evidence_ids: list[str] = Field(default_factory=list)
    status: str = "supported"


class AgentFinding(BaseModel):
    role: str
    status: str
    conclusion: str
    claims: list[Claim] = Field(default_factory=list)
    counterarguments: list[str] = Field(default_factory=list)
    evidence_ids: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    initial_conclusion: str | None = None
    revision_reason: str | None = None


class DebateMessage(BaseModel):
    round_number: int
    agent_role: str
    message_type: str
    target_claim_id: str | None = None
    argument: str
    evidence_ids: list[str] = Field(default_factory=list)
    revision_status: str = "retained"


class CouncilRequest(BaseModel):
    question: str = Field(min_length=8, max_length=1000)
    symbol: str | None = Field(default=None, min_length=1, max_length=20)
    reporting_period: str | None = Field(default=None, max_length=80)
    document_ids: list[str] = Field(default_factory=list, max_length=50)
    focus: list[str] = Field(default_factory=list, max_length=8)
    specialists: list[str] = Field(default_factory=lambda: ["financial", "valuation", "risk", "evidence"], max_length=4)

    @model_validator(mode="after")
    def normalize(self):
        if not self.symbol and not self.document_ids:
            raise ValueError("Provide a company symbol or select at least one document.")
        allowed = {"financial", "valuation", "risk", "evidence"}
        if not self.specialists or set(self.specialists) - allowed:
            raise ValueError("Select one or more supported specialist roles.")
        self.symbol = self.symbol.strip().upper() if self.symbol else None
        return self


class CouncilCreateResponse(BaseModel):
    id: str
    status: CouncilStage


class CouncilSessionView(BaseModel):
    id: str
    question: str
    symbol: str | None
    status: CouncilStage
    stage: CouncilStage
    created_at: datetime
    updated_at: datetime
    report: dict | None = None
    events: list[dict] = Field(default_factory=list)


class CouncilReport(BaseModel):
    research_question: str
    executive_conclusion: str
    key_findings: list[str]
    supporting_arguments: list[str]
    opposing_arguments: list[str]
    material_disagreements: list[str]
    unresolved_questions: list[str]
    evidence_quality: str
    limitations: list[str]
    sources: list[EvidenceReference]
    methodology: str
    generated_at: datetime
    completion_status: str
