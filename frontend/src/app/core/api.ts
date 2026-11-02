import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import {
  AdminUser, AnalysisOut, AnalysisPage, AnalysisStats, AnalysisUpdate, Article, ArticleEdit, AuthConfig, Comment, Health,
  OfficialSource, OfficialSourceIn, PlatformStats, Post, PostPage, Preferences, PublicUser, Role, StatCatalog, StatSeries, StatSeriesPair, User, Workflow,
} from './models';
import { t } from './i18n';

@Injectable({ providedIn: 'root' })
export class Api {
  private readonly http = inject(HttpClient);
  private readonly base = '/api';

  createAnalysis(payload: { text: string; urls: string[]; files: File[] }) {
    const form = new FormData();
    form.append('text', payload.text);
    form.append('urls', JSON.stringify(payload.urls));
    payload.files.forEach((f) => form.append('files', f, f.name));
    return this.http.post<AnalysisOut>(`${this.base}/analyses`, form);
  }

  getAnalysis(id: string) {
    return this.http.get<AnalysisOut>(`${this.base}/analyses/${id}`);
  }

  listAnalyses(opts: {
    q?: string; verdict?: string | null; workflow?: Workflow | null; tag?: string | null; limit?: number; offset?: number;
  } = {}) {
    let params = new HttpParams().set('limit', opts.limit ?? 20).set('offset', opts.offset ?? 0);
    if (opts.q) params = params.set('q', opts.q);
    if (opts.verdict) params = params.set('verdict', opts.verdict);
    if (opts.workflow) params = params.set('workflow', opts.workflow);
    if (opts.tag) params = params.set('tag', opts.tag);
    return this.http.get<AnalysisPage>(`${this.base}/analyses`, { params });
  }

  updateAnalysis(id: string, patch: AnalysisUpdate) {
    return this.http.patch<AnalysisOut>(`${this.base}/analyses/${id}`, patch);
  }

  analysisStats() {
    return this.http.get<AnalysisStats>(`${this.base}/analyses/stats`);
  }

  readonly exportUrl = '/api/analyses/export.csv';

  deleteAnalysis(id: string) {
    return this.http.delete<void>(`${this.base}/analyses/${id}`);
  }

  regenerateArticle(id: string) {
    return this.http.post<Article>(`${this.base}/analyses/${id}/article`, {});
  }

  editArticle(id: string, article: ArticleEdit) {
    return this.http.put<Article>(`${this.base}/analyses/${id}/article`, article);
  }

  /** Publie l'article complet ou sa version courte sur le fil, avec un texte éventuellement retouché. */
  publishArticle(id: string, format: 'article' | 'court', body?: string) {
    return this.http.post<Post>(`${this.base}/analyses/${id}/publish`, { format, body: body ?? null });
  }

  articleUrl(id: string, format: 'md' | 'html') {
    return `${this.base}/analyses/${id}/article.${format}`;
  }

  getSettings() {
    return this.http.get<Preferences>(`${this.base}/settings`);
  }

  saveSettings(prefs: Preferences) {
    return this.http.put<Preferences>(`${this.base}/settings`, prefs);
  }

  health() {
    return this.http.get<Health>(`${this.base}/health`);
  }

  // ---------- comptes ----------
  authConfig() { return this.http.get<AuthConfig>(`${this.base}/auth/config`); }
  me() { return this.http.get<User>(`${this.base}/auth/me`); }
  login(email: string, password: string) { return this.http.post<User>(`${this.base}/auth/login`, { email, password }); }
  register(payload: { email: string; password: string; display_name: string; organization: string }) {
    return this.http.post<User>(`${this.base}/auth/register`, payload);
  }
  logout() { return this.http.post<void>(`${this.base}/auth/logout`, {}); }
  updateMe(patch: Partial<Pick<User, 'display_name' | 'organization' | 'bio'>>) {
    return this.http.patch<User>(`${this.base}/auth/me`, patch);
  }
  changePassword(current_password: string, new_password: string) {
    return this.http.post<void>(`${this.base}/auth/password`, { current_password, new_password });
  }
  profile(id: string) { return this.http.get<PublicUser>(`${this.base}/users/${id}`); }

  // ---------- réseau social ----------
  feed(opts: { q?: string; author?: string; limit?: number; offset?: number } = {}) {
    let params = new HttpParams().set('limit', opts.limit ?? 20).set('offset', opts.offset ?? 0);
    if (opts.q) params = params.set('q', opts.q);
    if (opts.author) params = params.set('author', opts.author);
    return this.http.get<PostPage>(`${this.base}/posts`, { params });
  }
  createPost(payload: { body: string; analysisId?: string | null; image?: File | null }) {
    const form = new FormData();
    form.append('body', payload.body);
    if (payload.analysisId) form.append('analysis_id', payload.analysisId);
    if (payload.image) form.append('image', payload.image, payload.image.name);
    return this.http.post<Post>(`${this.base}/posts`, form);
  }
  editPost(id: string, body: string) { return this.http.patch<Post>(`${this.base}/posts/${id}`, { body }); }
  deletePost(id: string) { return this.http.delete<void>(`${this.base}/posts/${id}`); }
  like(id: string, on: boolean) {
    const url = `${this.base}/posts/${id}/like`;
    return on ? this.http.put<Post>(url, {}) : this.http.delete<Post>(url);
  }
  comments(postId: string) { return this.http.get<Comment[]>(`${this.base}/posts/${postId}/comments`); }
  addComment(postId: string, body: string) {
    return this.http.post<Comment[]>(`${this.base}/posts/${postId}/comments`, { body });
  }
  deleteComment(postId: string, commentId: string) {
    return this.http.delete<void>(`${this.base}/posts/${postId}/comments/${commentId}`);
  }

  getPost(id: string) { return this.http.get<Post>(`${this.base}/posts/${id}`); }

  // ---------- annuaire des sources officielles ----------
  sources(q = '', all = false) {
    return this.http.get<OfficialSource[]>(`${this.base}/sources`, { params: { q, all } });
  }
  createSource(s: OfficialSourceIn) { return this.http.post<OfficialSource>(`${this.base}/sources`, s); }
  updateSource(id: string, s: OfficialSourceIn) { return this.http.put<OfficialSource>(`${this.base}/sources/${id}`, s); }
  deleteSource(id: string) { return this.http.delete<void>(`${this.base}/sources/${id}`); }

  // ---------- statistiques ----------
  statsCatalog() { return this.http.get<StatCatalog>(`${this.base}/stats/catalog`); }
  statsSeries(indicator: string, country: string, years = 20) {
    return this.http.get<StatSeriesPair>(`${this.base}/stats/series`, { params: { indicator, country, years } });
  }
  statsCompare(indicator: string, countries: string[]) {
    return this.http.get<StatSeries[]>(`${this.base}/stats/compare`, { params: { indicator, countries: countries.join(',') } });
  }
  statsMadagascar() { return this.http.get<StatSeries[]>(`${this.base}/stats/madagascar`); }

  // ---------- administration ----------
  adminStats() { return this.http.get<PlatformStats>(`${this.base}/admin/stats`); }
  adminAnalysisStats() { return this.http.get<AnalysisStats>(`${this.base}/admin/analyses/stats`); }
  adminUsers(q = '') { return this.http.get<AdminUser[]>(`${this.base}/admin/users`, { params: { q } }); }
  adminUpdateUser(id: string, patch: { role?: Role; active?: boolean }) {
    return this.http.patch<AdminUser>(`${this.base}/admin/users/${id}`, patch);
  }
  adminPosts(opts: { q?: string; limit?: number; offset?: number } = {}) {
    let params = new HttpParams().set('limit', opts.limit ?? 30).set('offset', opts.offset ?? 0);
    if (opts.q) params = params.set('q', opts.q);
    return this.http.get<PostPage>(`${this.base}/admin/posts`, { params });
  }
  setHidden(id: string, hidden: boolean) {
    const url = `${this.base}/admin/posts/${id}/hidden`;
    return hidden ? this.http.put<Post>(url, {}) : this.http.delete<Post>(url);
  }
}

/** Message d'erreur lisible à partir d'une réponse FastAPI. */
export function errorMessage(err: unknown): string {
  const e = err as { status?: number; error?: { detail?: unknown } };
  const detail = e?.error?.detail;
  if (typeof detail === 'string') return t(detail);
  if (Array.isArray(detail) && detail.length) return String((detail[0] as { msg?: string }).msg ?? t('Requête invalide'));
  if (e?.status === 0) return t('Serveur injoignable : vérifiez que le backend est démarré.');
  return t('Une erreur est survenue. Réessayez dans un instant.');
}
