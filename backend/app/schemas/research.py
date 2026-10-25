from datetime import datetime
from pydantic import BaseModel, Field


class ResearchRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=20, examples=["RELIANCE"])
    question: str = Field(default="Provide an evidence-led company research brief.", max_length=1000)


class Finding(BaseModel):
    agent: str
    title: str
    detail: str
    confidence_label: str = "unavailable"
    confidence_method: str = "Evidence-completeness label, not a probability or investment-success estimate."
    evidence: list[str] = []
    limitations: list[str] = []


class AgentEvent(BaseModel):
    agent: str
    status: str
    timestamp: datetime
    iteration: int
    detail: str


class ResearchResponse(BaseModel):
    run_id: str
    symbol: str
    generated_at: datetime
    summary: str
    findings: list[Finding]
    warnings: list[str]
    activity: list[AgentEvent]
    provenance: dict[str, dict] = Field(default_factory=dict)
    disclaimer: str


class PortfolioRequest(BaseModel):
    holdings: dict[str, float]


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    symbol: str | None = Field(default=None, max_length=20)


class DocumentTextRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=20, max_length=200000)
    company: str | None = Field(default=None, max_length=20)
