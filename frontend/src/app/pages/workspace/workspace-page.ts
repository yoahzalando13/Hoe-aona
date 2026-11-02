import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { GLOBAL_VERDICTS, WORKFLOWS, formatScore, kindIcon, toneColor, verdictLabel, workflowLabel } from '../../core/format';
import { AnalysisListItem, AnalysisStats, GlobalVerdict, Workflow } from '../../core/models';
import { Icon } from '../../shared/icon';
import { ScoreRing } from '../../shared/score-ring';

const PAGE_SIZE = 25;

interface Draft { title: string; notes: string; tags: string; workflow: Workflow; }

@Component({
  selector: 'app-workspace-page',
  imports: [FormsModule, RouterLink, Icon, ScoreRing],
  templateUrl: './workspace-page.html',
  styleUrl: './workspace-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class WorkspacePage {
  private readonly api = inject(Api);

  protected readonly workflows = WORKFLOWS;
  protected readonly verdicts = GLOBAL_VERDICTS;
  protected readonly toneColor = toneColor;
  protected readonly kindIcon = kindIcon;
  protected readonly formatScore = formatScore;
  protected readonly verdictLabel = verdictLabel;
  protected readonly workflowLabel = workflowLabel;
  protected readonly exportUrl = this.api.exportUrl;

  protected readonly stats = signal<AnalysisStats | null>(null);
  protected readonly items = signal<AnalysisListItem[]>([]);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly loadingMore = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);

  protected readonly query = signal('');
  protected readonly workflow = signal<Workflow | null>(null);
  protected readonly verdict = signal<GlobalVerdict | null>(null);
  protected readonly tag = signal<string | null>(null);
  protected readonly hasMore = computed(() => this.items().length < this.total());
  protected readonly filtered = computed(() => !!(this.query() || this.workflow() || this.verdict() || this.tag()));

  protected readonly editId = signal<string | null>(null);
  protected readonly confirmId = signal<string | null>(null);
  protected readonly saving = signal(false);
  protected draft: Draft = { title: '', notes: '', tags: '', workflow: 'a_traiter' };

  protected readonly verdictBars = computed(() => {
    const s = this.stats();
    if (!s || !s.total) return [];
    return this.verdicts
      .map((v) => ({ ...v, count: s.by_verdict[v.key] ?? 0, share: ((s.by_verdict[v.key] ?? 0) / s.total) * 100 }))
      .filter((v) => v.count > 0);
  });

  private debounce: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.loadStats();
    this.load();
    inject(DestroyRef).onDestroy(() => { if (this.debounce) clearTimeout(this.debounce); });
  }

  private loadStats(): void {
    this.api.analysisStats().subscribe({ next: (s) => this.stats.set(s) });
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.listAnalyses(this.filters(0)).subscribe({
      next: (page) => { this.items.set(page.items); this.total.set(page.total); this.loading.set(false); },
      error: (err) => { this.error.set(errorMessage(err)); this.loading.set(false); },
    });
  }

  protected loadMore(): void {
    this.loadingMore.set(true);
    this.api.listAnalyses(this.filters(this.items().length)).subscribe({
      next: (page) => {
        this.items.update((list) => [...list, ...page.items]);
        this.total.set(page.total);
        this.loadingMore.set(false);
      },
      error: (err) => { this.error.set(errorMessage(err)); this.loadingMore.set(false); },
    });
  }

  private filters(offset: number) {
    return { q: this.query().trim(), workflow: this.workflow(), verdict: this.verdict(), tag: this.tag(), limit: PAGE_SIZE, offset };
  }

  protected onQuery(value: string): void {
    this.query.set(value);
    if (this.debounce) clearTimeout(this.debounce);
    this.debounce = setTimeout(() => this.load(), 300);
  }

  protected setWorkflow(w: Workflow | null): void { this.workflow.set(this.workflow() === w ? null : w); this.load(); }
  protected setVerdict(v: GlobalVerdict | null): void { this.verdict.set(this.verdict() === v ? null : v); this.load(); }
  protected setTag(t: string | null): void { this.tag.set(this.tag() === t ? null : t); this.load(); }

  protected resetFilters(): void {
    this.query.set(''); this.workflow.set(null); this.verdict.set(null); this.tag.set(null);
    this.load();
  }

  protected edit(item: AnalysisListItem): void {
    this.confirmId.set(null);
    if (this.editId() === item.id) { this.editId.set(null); return; }
    this.draft = { title: item.title, notes: item.notes, tags: item.tags.join(', '), workflow: item.workflow };
    this.editId.set(item.id);
  }

  protected save(item: AnalysisListItem): void {
    const tags = this.draft.tags.split(',').map((t) => t.trim()).filter(Boolean);
    this.saving.set(true);
    this.api.updateAnalysis(item.id, {
      title: this.draft.title.trim() || item.title, notes: this.draft.notes, tags, workflow: this.draft.workflow,
    }).subscribe({
      next: (a) => {
        this.items.update((list) => list.map((i) => (i.id === a.id
          ? { ...i, title: a.title, notes: a.notes, tags: a.tags, workflow: a.workflow } : i)));
        this.saving.set(false);
        this.editId.set(null);
        this.loadStats();
        this.flash('Fiche enregistrée');
      },
      error: (err) => { this.error.set(errorMessage(err)); this.saving.set(false); },
    });
  }

  protected quickWorkflow(item: AnalysisListItem, workflow: Workflow): void {
    this.api.updateAnalysis(item.id, { workflow }).subscribe({
      next: (a) => {
        this.items.update((list) => list.map((i) => (i.id === a.id ? { ...i, workflow: a.workflow } : i)));
        this.loadStats();
      },
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected remove(item: AnalysisListItem): void {
    this.api.deleteAnalysis(item.id).subscribe({
      next: () => {
        this.items.update((list) => list.filter((i) => i.id !== item.id));
        this.total.update((t) => Math.max(0, t - 1));
        this.confirmId.set(null);
        this.loadStats();
        this.flash('Analyse supprimée');
      },
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected count(w: Workflow): number {
    return this.stats()?.by_workflow[w] ?? 0;
  }

  protected date(iso: string): string {
    return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'short', year: 'numeric' });
  }

  private flash(message: string): void {
    this.notice.set(message);
    setTimeout(() => this.notice.set(null), 2400);
  }
}
