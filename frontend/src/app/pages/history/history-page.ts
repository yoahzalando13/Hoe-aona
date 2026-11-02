import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { GLOBAL_VERDICTS, dayGroup, kindIcon, toneColor } from '../../core/format';
import { AnalysisListItem, GlobalVerdict } from '../../core/models';
import { Icon } from '../../shared/icon';
import { ScoreRing } from '../../shared/score-ring';
import { LOCALE, PluralPipe, TPipe, t } from '../../core/i18n';

const PAGE_SIZE = 20;
const STATUS_LABEL: Record<string, string> = { pending: t('En attente'), running: t('En cours'), error: t('Échec') };
const KIND_LABEL: Record<string, string> = {
  text: t('Texte'), image: t('Image'), document: t('Document'), audio: t('Audio'), url: t('Lien'), mixte: t('Plusieurs données'),
};

@Component({
  selector: 'app-history-page',
  imports: [FormsModule, RouterLink, Icon, ScoreRing, TPipe, PluralPipe],
  templateUrl: './history-page.html',
  styleUrl: './history-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HistoryPage {
  private readonly api = inject(Api);

  protected readonly verdicts = GLOBAL_VERDICTS;
  protected readonly toneColor = toneColor;
  protected readonly kindIcon = kindIcon;

  protected readonly query = signal('');
  protected readonly verdict = signal<GlobalVerdict | null>(null);
  protected readonly items = signal<AnalysisListItem[]>([]);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly loadingMore = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly confirmId = signal<string | null>(null);

  protected readonly groups = computed(() => {
    const out: { label: string; items: AnalysisListItem[] }[] = [];
    for (const item of this.items()) {
      const label = dayGroup(item.created_at);
      const last = out.at(-1);
      if (last?.label === label) last.items.push(item);
      else out.push({ label, items: [item] });
    }
    return out;
  });
  protected readonly hasMore = computed(() => this.items().length < this.total());

  private debounce: ReturnType<typeof setTimeout> | null = null;
  private poll: ReturnType<typeof setInterval> | null = null;

  constructor() {
    this.load();
    // Rafraîchit la liste tant qu'une analyse est en cours.
    this.poll = setInterval(() => {
      if (this.items().some((i) => i.status === 'pending' || i.status === 'running')) this.load(true);
    }, 4000);
    inject(DestroyRef).onDestroy(() => {
      if (this.poll) clearInterval(this.poll);
      if (this.debounce) clearTimeout(this.debounce);
    });
  }

  protected onQuery(value: string): void {
    this.query.set(value);
    if (this.debounce) clearTimeout(this.debounce);
    this.debounce = setTimeout(() => this.load(), 300);
  }

  protected setVerdict(v: GlobalVerdict | null): void {
    this.verdict.set(this.verdict() === v ? null : v);
    this.load();
  }

  protected load(silent = false): void {
    if (!silent) this.loading.set(true);
    this.error.set(null);
    const limit = silent ? Math.max(this.items().length, PAGE_SIZE) : PAGE_SIZE;
    this.api.listAnalyses({ q: this.query().trim(), verdict: this.verdict(), limit, offset: 0 }).subscribe({
      next: (page) => {
        this.items.set(page.items);
        this.total.set(page.total);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.loading.set(false);
      },
    });
  }

  protected loadMore(): void {
    this.loadingMore.set(true);
    this.api
      .listAnalyses({ q: this.query().trim(), verdict: this.verdict(), limit: PAGE_SIZE, offset: this.items().length })
      .subscribe({
        next: (page) => {
          this.items.update((list) => [...list, ...page.items]);
          this.total.set(page.total);
          this.loadingMore.set(false);
        },
        error: (err) => {
          this.error.set(errorMessage(err));
          this.loadingMore.set(false);
        },
      });
  }

  protected askDelete(event: Event, id: string): void {
    event.preventDefault();
    event.stopPropagation();
    this.confirmId.set(id);
  }

  protected cancelDelete(event: Event): void {
    event.preventDefault();
    event.stopPropagation();
    this.confirmId.set(null);
  }

  protected confirmDelete(event: Event, id: string): void {
    event.preventDefault();
    event.stopPropagation();
    this.api.deleteAnalysis(id).subscribe({
      next: () => {
        this.items.update((list) => list.filter((i) => i.id !== id));
        this.total.update((t) => Math.max(0, t - 1));
        this.confirmId.set(null);
      },
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected subtitle(item: AnalysisListItem): string {
    const kind = KIND_LABEL[item.input_kind] ?? t('Analyse');
    const time = new Date(item.created_at).toLocaleString(LOCALE, {
      weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    });
    return `${kind}, ${time}`;
  }

  protected statusLabel(item: AnalysisListItem): string | null {
    return STATUS_LABEL[item.status] ?? null;
  }
}
