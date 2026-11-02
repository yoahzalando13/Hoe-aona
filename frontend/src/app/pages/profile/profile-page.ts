import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal, untracked } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { Auth } from '../../core/auth';
import { avatarTone, initials } from '../../core/format';
import { Post, PublicUser } from '../../core/models';
import { Icon } from '../../shared/icon';
import { PostCard } from '../../shared/post-card';
import { PluralPipe, TPipe, t } from '../../core/i18n';

@Component({
  selector: 'app-profile-page',
  imports: [DatePipe, FormsModule, RouterLink, Icon, PostCard, TPipe, PluralPipe],
  templateUrl: './profile-page.html',
  styleUrl: './profile-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ProfilePage {
  readonly id = input.required<string>();

  private readonly api = inject(Api);
  protected readonly auth = inject(Auth);
  protected readonly initials = initials;
  protected readonly avatarTone = avatarTone;

  protected readonly profile = signal<PublicUser | null>(null);
  protected readonly posts = signal<Post[]>([]);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);
  protected readonly isMe = computed(() => this.auth.user()?.id === this.id());

  protected readonly editing = signal(false);
  protected readonly saving = signal(false);
  protected readonly formError = signal<string | null>(null);
  protected form = { display_name: '', organization: '', bio: '' };
  protected pwd = { current: '', next: '' };
  protected readonly pwdBusy = signal(false);
  protected readonly pwdError = signal<string | null>(null);

  constructor() {
    effect(() => {
      const id = this.id();
      untracked(() => this.load(id));
    });
  }

  private load(id: string): void {
    this.loading.set(true);
    this.error.set(null);
    this.editing.set(false);
    this.api.profile(id).subscribe({
      next: (p) => { this.profile.set(p); this.loading.set(false); },
      error: (err) => { this.error.set(errorMessage(err)); this.loading.set(false); },
    });
    this.api.feed({ author: id, limit: 30 }).subscribe({
      next: (page) => { this.posts.set(page.items); this.total.set(page.total); },
    });
  }

  protected startEdit(): void {
    const me = this.auth.user();
    if (!me) return;
    this.form = { display_name: me.display_name, organization: me.organization, bio: me.bio };
    this.formError.set(null);
    this.editing.set(true);
  }

  protected save(): void {
    this.saving.set(true);
    this.formError.set(null);
    this.api.updateMe({ ...this.form }).subscribe({
      next: (u) => {
        this.auth.set(u);
        this.profile.update((p) => (p ? { ...p, display_name: u.display_name, organization: u.organization, bio: u.bio } : p));
        this.saving.set(false);
        this.editing.set(false);
        this.flash(t('Profil mis à jour'));
      },
      error: (err) => { this.formError.set(errorMessage(err)); this.saving.set(false); },
    });
  }

  protected changePassword(): void {
    this.pwdBusy.set(true);
    this.pwdError.set(null);
    this.api.changePassword(this.pwd.current, this.pwd.next).subscribe({
      next: () => {
        this.pwd = { current: '', next: '' };
        this.pwdBusy.set(false);
        this.flash(t('Mot de passe modifié. Vos autres sessions ont été fermées.'));
      },
      error: (err) => { this.pwdError.set(errorMessage(err)); this.pwdBusy.set(false); },
    });
  }

  protected replace(post: Post): void {
    this.posts.update((list) => list.map((p) => (p.id === post.id ? post : p)));
  }

  protected drop(id: string): void {
    this.posts.update((list) => list.filter((p) => p.id !== id));
    this.total.update((t) => Math.max(0, t - 1));
  }

  private flash(message: string): void {
    this.notice.set(message);
    setTimeout(() => this.notice.set(null), 2800);
  }
}
