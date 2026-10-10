"""Pydantic models used both as Claude structured-output schemas and as persisted state."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SourceType = Literal["feedback", "customer_study", "sales", "option_list", "web", "assumption"]


class EvidenceRef(BaseModel):
    source_type: SourceType
    ref: str = Field(description="feedback ID (e.g. G60-0123), STUDY:<market>:<attribute>, SALES:<market>, OPTIONS:<item>, a URL, or 'assumption'")
    detail: str = Field(description="Short verbatim quote, number, or fact taken from the source")
    market: str = Field(description="EU, CN, US, RoW or ALL")
    supports: bool = Field(description="True if this evidence supports the claim, False if it contradicts it")


class Insight(BaseModel):
    id: str = Field(description="Stable short id like INS-01")
    title: str
    description: str = Field(description="The customer need, pain point or opportunity in customer language")
    insight_type: Literal["pain_point", "unmet_need", "delighter_to_keep", "emerging_trend"]
    markets: list[str]
    vfc_topics: list[str] = Field(description="Exact VFC topic names from the statistics table this insight is based on")
    evidence: list[EvidenceRef]
    evidence_basis: Literal["evidence_based", "mixed", "assumption_based"]
    conflicting_signals: list[str] = Field(description="Where sources or markets disagree")
    data_gaps: list[str] = Field(description="What is missing to be confident")


class InsightSet(BaseModel):
    insights: list[Insight]
    overall_caveats: list[str]


class FactorJudgement(BaseModel):
    score: int = Field(description="1 (very low) to 5 (very high)")
    justification: str


class Requirement(BaseModel):
    id: str = Field(description="Stable short id like REQ-01")
    title: str
    statement: str = Field(description="Customer-facing requirement: 'Customers in <market> shall be able to ...' - no engineering specs")
    customer_value: str
    target_markets: list[str]
    linked_insight_ids: list[str]
    kano_category: Literal["basic", "performance", "delighter"]
    current_offer_note: str = Field(description="What the current option list already offers for this need, or 'not found in option list'")
    evidence: list[EvidenceRef]
    assumptions: list[str] = Field(description="Forward-looking assumptions (3-5 years ahead) that the requirement relies on")
    uncertainties: list[str]
    conflicting_evidence: list[str]
    customer_impact: FactorJudgement
    future_relevance: FactorJudgement
    competitive_gap: FactorJudgement
    confidence: Literal["high", "medium", "low"]


class RequirementSet(BaseModel):
    requirements: list[Requirement]


class Challenge(BaseModel):
    counter_arguments: list[str]
    missing_evidence: list[str]
    alternative_interpretation: str
    risk_if_wrong: str
    recommendation: Literal["keep", "revise", "postpone", "reject"]
    recommendation_rationale: str
