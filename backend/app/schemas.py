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
    ui_language: Literal["fr", "en", "mg"] | None = None  # langue de l'interface du compte
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
    origin: Literal["wikipedia", "news", "web", "official", "community", "user_source"]
    category: str
    official: bool = False
    found_via: str = ""
    published_at: str | None = None
    excerpt: str = ""
    image_url: str | None = None
    reliability: float = 0.5
    reliability_reasons: list[str] = []
    relevance: float = 0.0
    stance: Stance = "context"
    confidence: float = 0.0
    justification: str = ""
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
    estimate_from_year: int | None = None
    stance: Stance = "context"
    comment: str = ""


class OfficialContact(BaseModel):
    id: str
    name: str
    acronym: str = ""
    category: str = ""
    website: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    verified_at: str | None = None
    reason: str = ""


ReasoningKind = Literal["contre_exemple", "absurde", "ordre_de_grandeur", "coherence", "sophisme"]
ReasoningOutcome = Literal["refute", "affaiblit", "compatible", "non_concluant"]


class ReasoningStep(BaseModel):
    text: str
    outcome: Literal["contredite", "compatible", "non_testable"] = "non_testable"
    explanation: str = ""
    refs: list[str] = []


class ReasoningTest(BaseModel):
    kind: ReasoningKind
    label: str
    outcome: ReasoningOutcome = "non_concluant"
    summary: str = ""
    hypothesis: str = ""
    steps: list[ReasoningStep] = []
    refs: list[str] = []
    effect: str = ""


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
    contacts: list[OfficialContact] = []
    reasoning: list[ReasoningTest] = []
    universal: bool = False
    score_before_reasoning: float | None = None
    reasoning_adjustment: float = 0.0


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
    key_points: list[str] = []  # « L'essentiel » : 3 à 4 phrases courtes
    social_post: str = ""  # suggestion de publication courte pour le fil média
    sources: list[ArticleSource] = []
    generated_by: Literal["llm", "modele"] = "modele"
    generated_at: datetime
    edited: bool = False  # relu et modifié par le journaliste


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


Workflow = Literal["a_traiter", "en_revue", "valide", "publie", "archive"]
Role = Literal["media", "admin"]


class ArticleEdit(BaseModel):
    """Modifications du journaliste sur l'article suggéré."""
    title: str = Field(..., min_length=1, max_length=200)
    lead: str = Field("", max_length=800)
    body_markdown: str = Field(..., min_length=1, max_length=20000)
    key_points: list[str] = Field([], max_length=6)
    social_post: str = Field("", max_length=2000)


class ArticlePublish(BaseModel):
    """Publication directe sur le fil : article complet ou publication courte, texte éventuellement retouché."""
    format: Literal["article", "court"] = "article"
    body: str | None = Field(None, max_length=20000)


class AgentEvent(BaseModel):
    """Étape du journal d'analyse : quel agent travaille, sur quoi, avec quel résultat."""
    at: float  # secondes écoulées depuis le début de l'analyse
    agent: str  # lecteur, detecteur, extracteur, chercheur, evaluateur, calculateur, redacteur
    message: str
    status: Literal["running", "done", "error", "info"] = "info"
    detail: str = ""
    tool: str = ""


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
    notes: str = ""
    tags: list[str] = []
    workflow: Workflow = "a_traiter"
    events: list[AgentEvent] = []
    owner_id: str | None = None
    owner_name: str | None = None
    editable: bool = False


class AnalysisListItem(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime | None = None
    status: Status
    title: str
    input_kind: str
    global_score: float | None = None
    verdict: GlobalVerdict | None = None
    notes: str = ""
    tags: list[str] = []
    workflow: Workflow = "a_traiter"


class AnalysisUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=160)
    notes: str | None = Field(None, max_length=10_000)
    tags: list[str] | None = Field(None, max_length=20)
    workflow: Workflow | None = None

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return v
        out: list[str] = []
        for tag in v:
            tag = " ".join(tag.strip().split())[:40]
            if tag and tag.lower() not in {t.lower() for t in out}:
                out.append(tag)
        return out


class TagCount(BaseModel):
    tag: str
    count: int


class AnalysisStats(BaseModel):
    total: int
    average_score: float | None = None
    by_verdict: dict[str, int] = {}
    by_workflow: dict[str, int] = {}
    by_status: dict[str, int] = {}
    tags: list[TagCount] = []


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


# ---------- comptes ----------
class UserOut(BaseModel):
    id: str
    created_at: datetime
    email: str
    display_name: str
    organization: str = ""
    bio: str = ""
    role: Role
    active: bool


class PublicUser(BaseModel):
    id: str
    created_at: datetime
    display_name: str
    organization: str = ""
    bio: str = ""
    role: Role
    posts_count: int = 0


class AdminUser(UserOut):
    analyses_count: int = 0
    posts_count: int = 0


class RegisterIn(BaseModel):
    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=8, max_length=200)
    display_name: str = Field(..., min_length=2, max_length=80)
    organization: str = Field("", max_length=120)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        v = v.strip().lower()
        local, _, domain = v.partition("@")
        if not local or "." not in domain or " " in v:
            raise ValueError("Adresse e-mail invalide")
        return v

    @field_validator("display_name", "organization")
    @classmethod
    def _strip(cls, v: str) -> str:
        return " ".join(v.split())


class LoginIn(BaseModel):
    email: str
    password: str


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(None, min_length=2, max_length=80)
    organization: str | None = Field(None, max_length=120)
    bio: str | None = Field(None, max_length=600)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=200)


class AdminUserUpdate(BaseModel):
    role: Role | None = None
    active: bool | None = None


class AuthConfig(BaseModel):
    allow_registration: bool
    has_users: bool


# ---------- réseau social ----------
class PostAnalysis(BaseModel):
    id: str
    title: str
    global_score: float | None = None
    verdict: GlobalVerdict | None = None
    input_kind: str = "text"


class PostOut(BaseModel):
    id: str
    created_at: datetime
    updated_at: datetime
    body: str
    author_id: str
    author_name: str
    author_organization: str = ""
    author_role: Role = "media"
    image_url: str | None = None
    analysis: PostAnalysis | None = None
    likes: int = 0
    liked: bool = False
    comments_count: int = 0
    hidden: bool = False
    can_edit: bool = False
    can_moderate: bool = False


class PostPage(BaseModel):
    items: list[PostOut]
    total: int


class PostUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=20000)


class CommentIn(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class CommentOut(BaseModel):
    id: str
    created_at: datetime
    body: str
    author_id: str
    author_name: str
    author_organization: str = ""
    can_delete: bool = False


class PlatformStats(BaseModel):
    users: int
    active_users: int
    admins: int
    analyses: int
    posts: int
    hidden_posts: int
    comments: int
    likes: int


# ---------- annuaire des sources officielles ----------
class OfficialSourceIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=160)
    acronym: str = Field("", max_length=30)
    category: str = Field("", max_length=80)
    website: str = Field("", max_length=300)
    email: str = Field("", max_length=300)
    phone: str = Field("", max_length=200)
    address: str = Field("", max_length=300)
    notes: str = Field("", max_length=2000)
    topics: list[str] = Field([], max_length=60)
    verified_at: str | None = Field(None, max_length=10)
    active: bool = True

    @field_validator("website")
    @classmethod
    def _url(cls, v: str) -> str:
        v = v.strip()
        if v and not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v

    @field_validator("topics")
    @classmethod
    def _topics(cls, v: list[str]) -> list[str]:
        out: list[str] = []
        for x in v:
            x = " ".join(x.strip().lower().split())[:60]
            if x and x not in out:
                out.append(x)
        return out


class OfficialSourceOut(OfficialSourceIn):
    id: str
    created_at: datetime
    updated_at: datetime
