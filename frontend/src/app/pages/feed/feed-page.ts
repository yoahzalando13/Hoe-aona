import { ChangeDetectionStrategy, Component, DestroyRef, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { Auth } from '../../core/auth';
import { avatarTone, initials, verdictLabel } from '../../core/format';
import { AnalysisListItem, Post } from '../../core/models';
import { Icon } from '../../shared/icon';
import { PostCard } from '../../shared/post-card';

const PAGE_SIZE = 15;
const MAX_IMAGE = 8 * 1024 * 1024;

@Component({
  selector: 'app-feed-page',
  imports: [FormsModule, RouterLink, Icon, PostCard],
  templateUrl: './feed-page.html',
  styleUrl: './feed-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FeedPage {
  /** `?analyse=<id>` : préremplit le formulaire avec une analyse de l'espace personnel. */
  readonly analyse = input<string>();

  private readonly api = inject(Api);
  private readonly router = inject(Router);
  protected readonly auth = inject(Auth);
  protected readonly initials = initials;
  protected readonly avatarTone = avatarTone;
  protected readonly verdictLabel = verdictLabel;

  protected readonly posts = signal<Post[]>([]);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly loadingMore = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly query = signal('');
  protected readonly hasMore = computed(() => this.posts().length < this.total());

  // Formulaire de publication
  protected body = '';
  protected readonly analyses = signal<AnalysisListItem[]>([]);
  protected readonly analysisId = signal<string | null>(null);
  protected readonly image = signal<File | null>(null);
  protected readonly preview = signal<string | null>(null);
  protected readonly publishing = signal(false);
  protected readonly composeError = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);
  protected readonly selectedAnalysis = computed(() => this.analyses().find((a) => a.id === this.analysisId()) ?? null);

  private debounce: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.load();
    this.api.listAnalyses({ limit: 100 }).subscribe({
      next: (page) => this.analyses.set(page.items.filter((a) => a.status === 'done')),
    });
    effect(() => {
      const id = this.analyse();
      if (!id) return;
      untracked(() => {
        this.analysisId.set(id);
        // L'analyse peut être hors des 100 dernières : on la charge pour l'afficher.
        this.api.getAnalysis(id).subscribe({
          next: (a) => {
            if (a.status !== 'done' || this.analyses().some((x) => x.id === a.id)) return;
            this.analyses.update((list) => [{ ...a, updated_at: a.updated_at }, ...list]);
          },
        });
      });
    });
    inject(DestroyRef).onDestroy(() => {
      if (this.debounce) clearTimeout(this.debounce);
      this.revokePreview();
    });
  }

  protected onQuery(value: string): void {
    this.query.set(value);
    if (this.debounce) clearTimeout(this.debounce);
    this.debounce = setTimeout(() => this.load(), 300);
  }

  protected load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.feed({ q: this.query().trim(), limit: PAGE_SIZE }).subscribe({
      next: (page) => { this.posts.set(page.items); this.total.set(page.total); this.loading.set(false); },
      error: (err) => { this.error.set(errorMessage(err)); this.loading.set(false); },
    });
  }

  protected loadMore(): void {
    this.loadingMore.set(true);
    this.api.feed({ q: this.query().trim(), limit: PAGE_SIZE, offset: this.posts().length }).subscribe({
      next: (page) => {
        const known = new Set(this.posts().map((p) => p.id));
        this.posts.update((list) => [...list, ...page.items.filter((p) => !known.has(p.id))]);
        this.total.set(page.total);
        this.loadingMore.set(false);
      },
      error: (err) => { this.error.set(errorMessage(err)); this.loadingMore.set(false); },
    });
  }

  protected pickImage(event: Event): void {
    const el = event.target as HTMLInputElement;
    const file = el.files?.[0] ?? null;
    el.value = '';
    if (!file) return;
    if (!file.type.startsWith('image/')) { this.composeError.set('Choisissez un fichier image.'); return; }
    if (file.size > MAX_IMAGE) { this.composeError.set('Image trop lourde (8 Mo maximum).'); return; }
    this.composeError.set(null);
    this.revokePreview();
    this.image.set(file);
    this.preview.set(URL.createObjectURL(file));
  }

  protected clearImage(): void {
    this.revokePreview();
    this.image.set(null);
  }

  protected clearAnalysis(): void {
    this.analysisId.set(null);
    if (this.analyse()) this.router.navigate([], { queryParams: { analyse: null }, replaceUrl: true });
  }

  protected canPublish(): boolean {
    return !this.publishing() && (!!this.body.trim() || !!this.image() || !!this.analysisId());
  }

  protected publish(): void {
    if (!this.canPublish()) return;
    this.publishing.set(true);
    this.composeError.set(null);
    this.api.createPost({ body: this.body.trim(), analysisId: this.analysisId(), image: this.image() }).subscribe({
      next: (post) => {
        this.posts.update((list) => [post, ...list]);
        this.total.update((t) => t + 1);
        this.body = '';
        this.clearImage();
        this.clearAnalysis();
        this.publishing.set(false);
        this.flash('Publication partagée');
      },
      error: (err) => { this.composeError.set(errorMessage(err)); this.publishing.set(false); },
    });
  }

  protected replace(post: Post): void {
    this.posts.update((list) => list.map((p) => (p.id === post.id ? post : p)));
  }

  protected drop(id: string): void {
    this.posts.update((list) => list.filter((p) => p.id !== id));
    this.total.update((t) => Math.max(0, t - 1));
  }

  private revokePreview(): void {
    const url = this.preview();
    if (url) URL.revokeObjectURL(url);
    this.preview.set(null);
  }

  private flash(message: string): void {
    this.notice.set(message);
    setTimeout(() => this.notice.set(null), 2400);
  }
}
