import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Subscription, switchMap, takeWhile, timer } from 'rxjs';
import { Api, errorMessage } from '../../core/api';
import {
  STANCE_LABEL, claimTone, formatNumber, formatScore, kindIcon, pct, relativeTime, scoreTone, stanceTone, toneColor,
} from '../../core/format';
import { MarkdownPipe } from '../../core/markdown';
import { AnalysisOut, Article, Claim, Criterion, ReasoningKind, ReasoningOutcome, Statistic } from '../../core/models';
import { Icon } from '../../shared/icon';
import { ScoreRing } from '../../shared/score-ring';

interface Segment { text: string; ref: string | null; }

const STEPS = [
  { at: 5, label: 'Lecture des données' },
  { at: 20, label: 'Détection des signatures IA' },
  { at: 30, label: 'Extraction des affirmations' },
  { at: 45, label: 'Recherche de preuves (MCP)' },
  { at: 75, label: 'Évaluation de la véracité' },
  { at: 88, label: 'Calcul des scores' },
  { at: 95, label: 'Rédaction de l’article' },
];

const CRITERION_ICON: Record<Criterion['key'], { icon: string; tone: string }> = {
  source: { icon: 'globe', tone: 'tone-blue' },
  veracity: { icon: 'verify', tone: 'tone-amber' },
  ai: { icon: 'robot', tone: 'tone-purple' },
};

const TOOL_LABELS: Record<string, string> = {
  wikipedia_search: 'Wikipedia',
  news_search: 'GDELT', web_search: 'Tavily', worldbank_indicator: 'Banque mondiale', fetch_page: 'Lecture de pages',
  news_madagascar: 'NewsData.io (presse malgache)', imf_indicator: 'FMI', platform_posts: 'Fil média Hoe-aona?',
  detect_ai_image: 'Sightengine',
};

@Component({
  selector: 'app-result-page',
  imports: [Icon, ScoreRing, MarkdownPipe, RouterLink, DatePipe],
  templateUrl: './result-page.html',
  styleUrl: './result-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ResultPage {
  readonly id = input<string>();

  private readonly api = inject(Api);
  private readonly router = inject(Router);
  private sub: Subscription | null = null;

  protected readonly analysis = signal<AnalysisOut | null>(null);
  protected readonly loading = signal(true);
  protected readonly empty = signal(false);
  protected readonly loadError = signal<string | null>(null);
  protected readonly regenerating = signal(false);
  protected readonly notice = signal<string | null>(null);
  protected readonly openDetails = signal<ReadonlySet<string>>(new Set());

  protected readonly result = computed(() => this.analysis()?.result ?? null);
  protected readonly steps = STEPS;
  protected readonly stanceLabel = STANCE_LABEL;
  protected readonly criterionIcon = CRITERION_ICON;
  protected readonly formatScore = formatScore;
  protected readonly formatNumber = formatNumber;
  protected readonly pct = pct;
  protected readonly scoreTone = scoreTone;
  protected readonly toneColor = toneColor;
  protected readonly claimTone = claimTone;
  protected readonly stanceTone = stanceTone;

  protected readonly inputsLabel = computed(() => {
    const inputs = this.result()?.inputs ?? [];
    if (!inputs.length) return this.analysis()?.title ?? '';
    const first = inputs[0].kind === 'text' ? 'Texte saisi' : inputs[0].name;
    return inputs.length > 1 ? `${first} + ${inputs.length - 1} autre${inputs.length > 2 ? 's' : ''}` : first;
  });
  protected readonly inputsIcon = computed(() => kindIcon(this.analysis()?.input_kind ?? 'text'));
  protected readonly analysedAgo = computed(() => {
    const a = this.analysis();
    return a ? relativeTime(a.updated_at) : '';
  });
  protected readonly toolsLabel = computed(() => (this.result()?.tools_used ?? []).map((t) => TOOL_LABELS[t] ?? t));

  constructor() {
    effect(() => {
      const id = this.id();
      untracked(() => this.load(id));
    });
    inject(DestroyRef).onDestroy(() => this.sub?.unsubscribe());
  }

  private load(id: string | undefined): void {
    this.sub?.unsubscribe();
    this.loading.set(true);
    this.empty.set(false);
    this.loadError.set(null);
    if (!id) {
      this.api.listAnalyses({ limit: 1 }).subscribe({
        next: (page) => {
          if (page.items.length) this.router.navigate(['/resultat', page.items[0].id], { replaceUrl: true });
          else { this.empty.set(true); this.loading.set(false); }
        },
        error: (err) => { this.loadError.set(errorMessage(err)); this.loading.set(false); },
      });
      return;
    }
    this.sub = timer(0, 1500)
      .pipe(
        switchMap(() => this.api.getAnalysis(id)),
        takeWhile((a) => a.status === 'pending' || a.status === 'running', true),
      )
      .subscribe({
        next: (a) => { this.analysis.set(a); this.loading.set(false); },
        error: (err) => { this.loadError.set(errorMessage(err)); this.loading.set(false); },
      });
  }

  protected stepState(at: number, progress: number): 'done' | 'current' | 'todo' {
    const next = STEPS.find((s) => s.at > at)?.at ?? 100;
    if (progress >= next) return 'done';
    if (progress >= at) return 'current';
    return 'todo';
  }

  protected toggleDetails(key: string): void {
    this.openDetails.update((set) => {
      const next = new Set(set);
      if (next.has(key)) next.delete(key); else next.add(key);
      return next;
    });
  }

  /** Découpe un argument en texte et références [E1]/[S1] cliquables. */
  protected segments(text: string): Segment[] {
    const out: Segment[] = [];
    let last = 0;
    for (const m of text.matchAll(/\[([ES]\d+)\]/g)) {
      if (m.index! > last) out.push({ text: text.slice(last, m.index), ref: null });
      out.push({ text: m[1], ref: m[1] });
      last = m.index! + m[0].length;
    }
    if (last < text.length) out.push({ text: text.slice(last), ref: null });
    return out;
  }

  protected anchor(claim: Claim, ref: string): string {
    return `preuve-${claim.id}-${ref}`;
  }

  protected scrollTo(id: string): void {
    const el = document.getElementById(id);
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    el?.classList.add('flash');
    setTimeout(() => el?.classList.remove('flash'), 1400);
  }

  protected sparkline(stat: Statistic): string {
    const pts = stat.series;
    if (pts.length < 2) return '';
    const values = pts.map((p) => p.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || 1;
    return pts
      .map((p, i) => `${((i / (pts.length - 1)) * 116 + 2).toFixed(1)},${(34 - ((p.value - min) / span) * 30).toFixed(1)}`)
      .join(' ');
  }

  protected hideImage(event: Event): void {
    (event.target as HTMLElement).style.display = 'none';
  }

  protected back(): void {
    if (history.length > 1) history.back();
    else this.router.navigate(['/espace']);
  }

  protected async share(): Promise<void> {
    const a = this.analysis();
    const r = this.result();
    if (!a || !r) return;
    const data = { title: `Hoe-aona? : ${r.verdict_label}`, text: `${a.title} : ${formatScore(r.global_score)}/10`, url: location.href };
    try {
      if (navigator.share) await navigator.share(data);
      else { await navigator.clipboard.writeText(data.url); this.flash('Lien copié'); }
    } catch { /* partage annulé */ }
  }

  protected scrollToArticle(): void {
    this.scrollTo('article');
  }

  private markdown(article: Article): string {
    const sources = article.sources.map((s) => `${s.n}. [${s.title}](${s.url}) — ${s.publisher}`).join('\n');
    return `# ${article.title}\n\n*${article.lead}*\n\n${article.body_markdown}\n\n## Sources\n\n${sources}\n`;
  }

  protected async copyArticle(article: Article): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.markdown(article));
      this.flash('Article copié en Markdown');
    } catch {
      this.flash('Copie impossible : utilisez le téléchargement');
    }
  }

  protected readonly thisYear = new Date().getFullYear();

  protected readonly reasoningIcon: Record<ReasoningKind, string> = {
    contre_exemple: 'search', absurde: 'layers', ordre_de_grandeur: 'chart', coherence: 'check', sophisme: 'alert',
  };
  protected readonly outcomeLabel: Record<ReasoningOutcome, string> = {
    refute: 'Réfute', affaiblit: 'Affaiblit', compatible: 'Compatible', non_concluant: 'Non concluant',
  };
  protected readonly stepLabel: Record<string, string> = {
    contredite: 'Démentie', compatible: 'Vérifiée', non_testable: 'Non testable',
  };

  protected outcomeTone(o: string): string {
    return o === 'refute' || o === 'contredite' ? 'bad' : o === 'affaiblit' ? 'mid'
      : o === 'compatible' ? 'good' : 'neutral';
  }

  /** Tests à montrer : on masque les « non concluants » sans contenu utile. */
  protected shownTests(claim: Claim) {
    return (claim.reasoning ?? []).filter((t) => t.outcome !== 'non_concluant' || t.steps.length || t.kind === 'sophisme');
  }

  protected signed(n: number): string {
    return (n > 0 ? '+' : '') + n.toFixed(1).replace('.', ',');
  }

  /** Écart entre l'année de la donnée et l'année en cours, pour signaler une statistique ancienne. */
  protected statAge(s: Statistic): number {
    return s.latest_year ? this.thisYear - s.latest_year : 99;
  }

  protected isEstimate(s: Statistic, year: number | null): boolean {
    return !!s.estimate_from_year && !!year && year >= s.estimate_from_year;
  }

  protected tel(phone: string): { label: string; href: string }[] {
    return phone.split('/').map((p) => p.trim()).filter(Boolean).map((label) => ({
      label, href: 'tel:' + label.replace(/\(.*?\)/g, '').replace(/[^\d+]/g, ''),
    }));
  }

  protected downloadUrl(format: 'md' | 'html'): string {
    return this.api.articleUrl(this.analysis()!.id, format);
  }

  protected regenerate(): void {
    const a = this.analysis();
    if (!a?.result) return;
    this.regenerating.set(true);
    this.api.regenerateArticle(a.id).subscribe({
      next: (article) => {
        this.analysis.set({ ...a, result: { ...a.result!, article } });
        this.regenerating.set(false);
        this.flash('Nouvel article rédigé');
      },
      error: (err) => { this.regenerating.set(false); this.flash(errorMessage(err)); },
    });
  }

  private flash(message: string): void {
    this.notice.set(message);
    setTimeout(() => this.notice.set(null), 2600);
  }
}
