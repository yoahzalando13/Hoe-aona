import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { Auth } from '../../core/auth';
import { GLOBAL_VERDICTS, WORKFLOWS, avatarTone, formatScore, initials, toneColor } from '../../core/format';
import { AdminUser, AnalysisStats, PlatformStats, Post, Role } from '../../core/models';
import { Icon } from '../../shared/icon';
import { PostCard } from '../../shared/post-card';
import { PluralPipe, TPipe } from '../../core/i18n';

type Tab = 'overview' | 'users' | 'posts';

@Component({
  selector: 'app-admin-page',
  imports: [DatePipe, FormsModule, RouterLink, Icon, PostCard, TPipe, PluralPipe],
  templateUrl: './admin-page.html',
  styleUrl: './admin-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AdminPage {
  private readonly api = inject(Api);
  protected readonly auth = inject(Auth);
  protected readonly initials = initials;
  protected readonly avatarTone = avatarTone;
  protected readonly formatScore = formatScore;
  protected readonly toneColor = toneColor;
  protected readonly verdicts = GLOBAL_VERDICTS;
  protected readonly workflows = WORKFLOWS;

  protected readonly tab = signal<Tab>('overview');
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);

  protected readonly stats = signal<PlatformStats | null>(null);
  protected readonly analysisStats = signal<AnalysisStats | null>(null);

  protected readonly users = signal<AdminUser[]>([]);
  protected readonly userQuery = signal('');
  protected readonly usersLoading = signal(false);

  protected readonly posts = signal<Post[]>([]);
  protected readonly postsTotal = signal(0);
  protected readonly postQuery = signal('');
  protected readonly postsLoading = signal(false);
  protected readonly onlyHidden = signal(false);
  protected readonly visiblePosts = computed(() => (this.onlyHidden() ? this.posts().filter((p) => p.hidden) : this.posts()));

  private debounce: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.loadOverview();
    inject(DestroyRef).onDestroy(() => { if (this.debounce) clearTimeout(this.debounce); });
  }

  protected open(tab: Tab): void {
    this.tab.set(tab);
    this.error.set(null);
    if (tab === 'overview') this.loadOverview();
    if (tab === 'users') this.loadUsers();
    if (tab === 'posts') this.loadPosts();
  }

  private loadOverview(): void {
    this.api.adminStats().subscribe({ next: (s) => this.stats.set(s), error: (e) => this.error.set(errorMessage(e)) });
    this.api.adminAnalysisStats().subscribe({ next: (s) => this.analysisStats.set(s) });
  }

  protected loadUsers(): void {
    this.usersLoading.set(true);
    this.api.adminUsers(this.userQuery().trim()).subscribe({
      next: (u) => { this.users.set(u); this.usersLoading.set(false); },
      error: (e) => { this.error.set(errorMessage(e)); this.usersLoading.set(false); },
    });
  }

  protected loadPosts(): void {
    this.postsLoading.set(true);
    this.api.adminPosts({ q: this.postQuery().trim(), limit: 100 }).subscribe({
      next: (page) => { this.posts.set(page.items); this.postsTotal.set(page.total); this.postsLoading.set(false); },
      error: (e) => { this.error.set(errorMessage(e)); this.postsLoading.set(false); },
    });
  }

  protected search(kind: 'users' | 'posts', value: string): void {
    (kind === 'users' ? this.userQuery : this.postQuery).set(value);
    if (this.debounce) clearTimeout(this.debounce);
    this.debounce = setTimeout(() => (kind === 'users' ? this.loadUsers() : this.loadPosts()), 300);
  }

  protected setRole(u: AdminUser, role: Role): void {
    this.updateUser(u, { role }, role === 'admin' ? `${u.display_name} est administrateur` : role === 'reader' ? `${u.display_name} est lecteur` : `${u.display_name} est personnel média`);
  }

  protected toggleActive(u: AdminUser): void {
    this.updateUser(u, { active: !u.active }, u.active ? `Compte de ${u.display_name} désactivé` : `Compte de ${u.display_name} réactivé`);
  }

  private updateUser(u: AdminUser, patch: { role?: Role; active?: boolean }, message: string): void {
    this.error.set(null);
    this.api.adminUpdateUser(u.id, patch).subscribe({
      next: (updated) => {
        this.users.update((list) => list.map((x) => (x.id === updated.id ? updated : x)));
        this.flash(message);
      },
      error: (e) => {
        this.error.set(errorMessage(e));
        this.users.update((list) => [...list]); // rétablit la valeur affichée du sélecteur
      },
    });
  }

  protected replace(post: Post): void {
    this.posts.update((list) => list.map((p) => (p.id === post.id ? post : p)));
  }

  protected drop(id: string): void {
    this.posts.update((list) => list.filter((p) => p.id !== id));
    this.postsTotal.update((t) => Math.max(0, t - 1));
  }

  protected wf(key: string): number {
    return this.analysisStats()?.by_workflow[key] ?? 0;
  }

  protected vd(key: string): number {
    return this.analysisStats()?.by_verdict[key] ?? 0;
  }

  private flash(message: string): void {
    this.notice.set(message);
    setTimeout(() => this.notice.set(null), 2400);
  }
}
