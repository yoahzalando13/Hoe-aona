// Miroir des schémas Pydantic du backend (app/schemas.py)
export type Stance = 'supports' | 'refutes' | 'context';
export type ClaimVerdict = 'vrai' | 'plutot_vrai' | 'mitige' | 'non_verifiable' | 'plutot_faux' | 'faux';
export type GlobalVerdict = 'fiable' | 'plutot_fiable' | 'a_verifier' | 'douteux';
export type Status = 'pending' | 'running' | 'done' | 'error';
export type InputKind = 'text' | 'image' | 'document' | 'audio' | 'url';
export type Workflow = 'a_traiter' | 'en_revue' | 'valide' | 'publie' | 'archive';
/** reader : lecteur du fil (lire, aimer, commenter), sans fonctions de rédaction. */
export type Role = 'media' | 'admin' | 'reader';

export interface Preferences {
  weight_source: number;
  weight_veracity: number;
  weight_ai: number;
  deep_ai_detection: boolean;
  ai_exclusion_threshold: number;
  min_source_reliability: number;
  default_country: string;
  report_language: 'fr' | 'en' | 'mg';
  ui_language?: 'fr' | 'en' | 'mg' | null;
  history_retention_days: number;
}

export interface InputSummary {
  kind: InputKind;
  name: string;
  size: number | null;
  extracted_chars: number;
  ai_probability: number;
  ai_signals: string[];
  reliability: number | null;
  reliability_reasons: string[];
  url: string | null;
  note: string | null;
}

export interface Evidence {
  id: string;
  url: string;
  title: string;
  publisher: string;
  domain: string;
  origin: 'wikipedia' | 'news' | 'web' | 'official' | 'community' | 'user_source';
  category: string;
  official: boolean;
  found_via: string;
  published_at: string | null;
  excerpt: string;
  image_url: string | null;
  reliability: number;
  reliability_reasons: string[];
  relevance: number;
  stance: Stance;
  confidence: number;
  justification: string;
  ai_probability: number;
}

export interface Statistic {
  id: string;
  indicator_code: string;
  indicator_name: string;
  country: string;
  country_code: string;
  latest_year: number | null;
  latest_value: number | null;
  unit: string;
  series: { year: number; value: number }[];
  claimed_value: string | null;
  source_name: string;
  source_url: string;
  last_updated: string | null;
  estimate_from_year: number | null;
  stance: Stance;
  comment: string;
}

export interface Claim {
  id: string;
  text: string;
  search_query: string;
  truth_score: number;
  evidence_weight: number;
  verdict: ClaimVerdict;
  verdict_label: string;
  conclusion: string;
  arguments_for: string[];
  arguments_against: string[];
  evidence: Evidence[];
  statistics: Statistic[];
  contacts: OfficialContact[];
  reasoning: ReasoningTest[];
  universal: boolean;
  score_before_reasoning: number | null;
  reasoning_adjustment: number;
}

export type ReasoningKind = 'contre_exemple' | 'absurde' | 'ordre_de_grandeur' | 'coherence' | 'sophisme';
export type ReasoningOutcome = 'refute' | 'affaiblit' | 'compatible' | 'non_concluant';

export interface ReasoningStep {
  text: string;
  outcome: 'contredite' | 'compatible' | 'non_testable';
  explanation: string;
  refs: string[];
}

export interface ReasoningTest {
  kind: ReasoningKind;
  label: string;
  outcome: ReasoningOutcome;
  summary: string;
  hypothesis: string;
  steps: ReasoningStep[];
  refs: string[];
  effect: string;
}

export interface OfficialContact {
  id: string;
  name: string;
  acronym: string;
  category: string;
  website: string;
  email: string;
  phone: string;
  address: string;
  verified_at: string | null;
  reason: string;
}

export interface Criterion {
  key: 'source' | 'veracity' | 'ai';
  label: string;
  score: number;
  summary: string;
  details: string[];
}

export interface ExcludedSource { url: string; title: string; reason: string; ai_probability: number; }
export interface ArticleSource { n: number; title: string; publisher: string; url: string; }

export interface Article {
  title: string;
  lead: string;
  body_markdown: string;
  tags: string[];
  key_points?: string[]; // absents des articles rédigés avant cette version
  social_post?: string;
  sources: ArticleSource[];
  generated_by: 'llm' | 'modele';
  generated_at: string;
  edited?: boolean;
}

export interface AnalysisResult {
  global_score: number;
  verdict: GlobalVerdict;
  verdict_label: string;
  summary: string;
  topic: string;
  criteria: Criterion[];
  claims: Claim[];
  inputs: InputSummary[];
  excluded_sources: ExcludedSource[];
  article: Article | null;
  warnings: string[];
  tools_used: string[];
  weights: Record<string, number>;
}

export type AgentKey = 'lecteur' | 'detecteur' | 'extracteur' | 'chercheur' | 'evaluateur' | 'calculateur' | 'redacteur';

export interface AgentEvent {
  at: number;
  agent: AgentKey;
  message: string;
  status: 'running' | 'done' | 'error' | 'info';
  detail: string;
  tool: string;
  duration?: number;
}

export interface AnalysisOut {
  id: string;
  created_at: string;
  updated_at: string;
  status: Status;
  progress: number;
  step: string;
  title: string;
  input_kind: string;
  global_score: number | null;
  verdict: GlobalVerdict | null;
  result: AnalysisResult | null;
  error: string | null;
  notes: string;
  tags: string[];
  workflow: Workflow;
  events: AgentEvent[];
  owner_id: string | null;
  owner_name: string | null;
  editable: boolean;
}

export interface AnalysisListItem {
  id: string;
  created_at: string;
  status: Status;
  title: string;
  input_kind: string;
  global_score: number | null;
  verdict: GlobalVerdict | null;
  updated_at?: string | null;
  notes: string;
  tags: string[];
  workflow: Workflow;
}

export interface AnalysisUpdate { title?: string; notes?: string; tags?: string[]; workflow?: Workflow; }

export interface AnalysisStats {
  total: number;
  average_score: number | null;
  by_verdict: Record<string, number>;
  by_workflow: Record<string, number>;
  by_status: Record<string, number>;
  tags: { tag: string; count: number }[];
}

export interface AnalysisPage { items: AnalysisListItem[]; total: number; }

export interface ProviderStatus {
  key: string;
  label: string;
  role: string;
  configured: boolean;
  requires_key: boolean;
  signup_url: string | null;
}

export interface Health {
  status: string;
  mcp_mode: string;
  mcp_tools: string[];
  mcp_errors: string[];
  providers: ProviderStatus[];
}

// ---------- comptes ----------
export interface User {
  id: string;
  created_at: string;
  email: string;
  display_name: string;
  organization: string;
  bio: string;
  role: Role;
  active: boolean;
}

export interface AdminUser extends User { analyses_count: number; posts_count: number; }

export interface PublicUser {
  id: string;
  created_at: string;
  display_name: string;
  organization: string;
  bio: string;
  role: Role;
  posts_count: number;
}

export interface AuthConfig { allow_registration: boolean; has_users: boolean; }

// ---------- réseau social ----------
export interface PostAnalysis {
  id: string;
  title: string;
  global_score: number | null;
  verdict: GlobalVerdict | null;
  input_kind: string;
}

export interface Post {
  id: string;
  created_at: string;
  updated_at: string;
  body: string;
  author_id: string;
  author_name: string;
  author_organization: string;
  author_role: Role;
  image_url: string | null;
  analysis: PostAnalysis | null;
  likes: number;
  liked: boolean;
  comments_count: number;
  hidden: boolean;
  can_edit: boolean;
  can_moderate: boolean;
}

export interface PostPage { items: Post[]; total: number; }

export interface Comment {
  id: string;
  created_at: string;
  body: string;
  author_id: string;
  author_name: string;
  author_organization: string;
  can_delete: boolean;
}

export interface PlatformStats {
  users: number;
  active_users: number;
  admins: number;
  analyses: number;
  posts: number;
  hidden_posts: number;
  comments: number;
  likes: number;
}

// ---------- annuaire des sources officielles ----------
export interface OfficialSourceIn {
  name: string;
  acronym: string;
  category: string;
  website: string;
  email: string;
  phone: string;
  address: string;
  notes: string;
  topics: string[];
  verified_at: string | null;
  active: boolean;
}

export interface OfficialSource extends OfficialSourceIn { id: string; created_at: string; updated_at: string; }

// ---------- statistiques ----------
export interface StatPoint { year: number; value: number; }
export interface StatIndicator { code: string; label: string; unit: string; theme: string; imf: boolean; }
export interface StatCountry { code: string; name: string; region: boolean; }
export interface StatCatalog { indicators: StatIndicator[]; themes: string[]; countries: StatCountry[]; neighbours: string[]; }

export interface StatSeries {
  ok: boolean;
  provider: 'worldbank' | 'imf';
  indicator_code: string;
  indicator_name?: string;
  unit?: string;
  country: string;
  country_code: string;
  series?: StatPoint[];
  latest_year?: number | null;
  latest_value?: number | null;
  last_updated?: string | null;
  estimate_from_year?: number | null;
  source_name?: string;
  source_url?: string;
  error?: string;
  imf?: StatSeries | null;
}
export interface StatSeriesPair { worldbank: StatSeries; imf: StatSeries | null; }

export interface ArticleEdit { title: string; lead: string; body_markdown: string; key_points: string[]; social_post: string; }

/** Activité de la plateforme par région et contenus truqués (données fictives tant que `demo` est vrai). */
export interface RegionActivity {
  code: string; name: string; capital: string; population: number;
  analyses: number; verifications: number; members: number; rate_per_100k: number; trend_pct: number | null;
  media_analysed: number; deepfakes: number; deepfake_rate: number;
}
export interface DeepfakeKind { kind: string; label: string; count: number; share: number; }
export interface DeepfakeMonth { month: string; analysed: number; flagged: number; rate: number; }
export interface PlatformActivity {
  demo: boolean; period_days: number; generated_on: string;
  totals: { analyses: number; verifications: number; members: number; rate_per_100k: number;
            media_analysed: number; deepfakes: number; deepfake_rate: number };
  regions: RegionActivity[]; deepfake_by_kind: DeepfakeKind[]; deepfake_monthly: DeepfakeMonth[];
}
