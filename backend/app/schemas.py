"""Schémas de données échangés entre le backend et l'application Angular."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Stance = Literal["supports", "refutes", "context"]
ClaimVerdict = Literal["vrai", "plutot_vrai", "mitige", "non_verifiable", "plutot_faux", "faux"]
GlobalVerdict = Literal["fiable", "plutot_fiable", "a_verifier", "douteux"]
Status = Literal["pending", "running", "done", "error"]
InputKind = Literal["text", "image", "document", "audio", "url"]


class Preferences(BaseModel):
    weight_source: int = Field(40, ge=0, le=100)
    weight_veracity: int = Field(40, ge=0, le=100)
    weight_ai: int = Field(20, ge=0, le=100)
    deep_ai_detection: bool = True
    ai_exclusion_threshold: float = Field(0.7, ge=0.5, le=0.99)
    min_source_reliability: float = Field(0.35, ge=0.0, le=0.9)
    default_country: str = "MDG"
    report_language: Literal["fr", "en", "mg"] = "fr"
    history_retention_days: int = Field(90, ge=1, le=3650)

    @field_validator("default_country")
    @classmethod
    def _iso3(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("Code pays ISO 3166-1 alpha-3 attendu (ex. MDG)")
        return v

    def normalized_weights(self) -> tuple[float, float, float]:
        total = self.weight_source + self.weight_veracity + self.weight_ai
        if total <= 0:
            return 0.4, 0.4, 0.2
        return (
            self.weight_source / total,
            self.weight_veracity / total,
            self.weight_ai / total,
        )


class InputSummary(BaseModel):
    kind: InputKind
    name: str
    size: int | None = None
    extracted_chars: int = 0
    ai_probability: float = 0.0
    ai_signals: list[str] = []
    reliability: float | None = None
    reliability_reasons: list[str] = []
    url: str | None = None
    note: str | None = None


class Evidence(BaseModel):
    id: str
    url: str
    title: str
    publisher: str
    domain: str
    origin: Literal["factcheck", "wikipedia", "news", "web", "user_source"]
    category: str
    published_at: str | None = None
    excerpt: str = ""
    image_url: str | None = None
    reliability: float = 0.5
    reliability_reasons: list[str] = []
    relevance: float = 0.0
    stance: Stance = "context"
    confidence: float = 0.0
    justification: str = ""
    rating: str | None = None
    ai_probability: float = 0.0


class StatPoint(BaseModel):
    year: int
    value: float


class Statistic(BaseModel):
    id: str
    indicator_code: str
    indicator_name: str
    country: str
    country_code: str
    latest_year: int | None = None
    latest_value: float | None = None
    unit: str = ""
    series: list[StatPoint] = []
    claimed_value: str | None = None
    source_name: str = "Banque mondiale, World Development Indicators"
    source_url: str
    last_updated: str | None = None
    stance: Stance = "context"
    comment: str = ""


class Claim(BaseModel):
    id: str
    text: str
    search_query: str
    truth_score: float = 5.0
    evidence_weight: float = 0.0
    verdict: ClaimVerdict = "non_verifiable"
    verdict_label: str = "Non vérifiable"
    conclusion: str = ""
    arguments_for: list[str] = []
    arguments_against: list[str] = []
    evidence: list[Evidence] = []
    statistics: list[Statistic] = []


class Criterion(BaseModel):
    key: Literal["source", "veracity", "ai"]
    label: str
    score: float
    summary: str
    details: list[str] = []


class ExcludedSource(BaseModel):
    url: str
    title: str
    reason: str
    ai_probability: float


class ArticleSource(BaseModel):
    n: int
    title: str
    publisher: str
    url: str


class Article(BaseModel):
    title: str
    lead: str
    body_markdown: str
    tags: list[str] = []
    sources: list[ArticleSource] = []
    generated_by: Literal["llm", "modele"] = "modele"
    generated_at: datetime


class AnalysisResult(BaseModel):
    global_score: float
    verdict: GlobalVerdict
    verdict_label: str
    summary: str
    topic: str = ""
    criteria: list[Criterion]
    claims: list[Claim]
    inputs: list[InputSummary]
    excluded_sources: list[ExcludedSource] = []
    article: Article | None = None
    warnings: list[str] = []
    tools_used: list[str] = []
    weights: dict[str, float] = {}


class AnalysisOut(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    status: Status
    progress: int
    step: str
    title: str
    input_kind: str
    global_score: float | None = None
    verdict: GlobalVerdict | None = None
    result: AnalysisResult | None = None
    error: str | None = None


class AnalysisListItem(BaseModel):
    id: str
    created_at: datetime
    status: Status
    title: str
    input_kind: str
    global_score: float | None = None
    verdict: GlobalVerdict | None = None


class AnalysisPage(BaseModel):
    items: list[AnalysisListItem]
    total: int


class ProviderStatus(BaseModel):
    key: str
    label: str
    role: str
    configured: bool
    requires_key: bool
    signup_url: str | None = None


class HealthOut(BaseModel):
    status: str
    mcp_mode: str
    mcp_tools: list[str]
    mcp_errors: list[str]
    providers: list[ProviderStatus]
