import { ChangeDetectionStrategy, Component, effect, inject, input, signal, untracked } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { Post } from '../../core/models';
import { Icon } from '../../shared/icon';
import { PostCard } from '../../shared/post-card';
import { TPipe } from '../../core/i18n';

@Component({
  selector: 'app-post-page',
  imports: [RouterLink, Icon, PostCard, TPipe],
  template: `
    <section class="page">
      <header class="appbar">
        <button type="button" class="icon-btn" (click)="back()" [attr.aria-label]="'Retour' | t"><app-icon name="back" /></button>
        <h1>{{ 'Publication' | t }}</h1>
      </header>
      @if (error()) {
        <p class="error-box" role="alert">{{ error() }}</p>
        <a class="btn" routerLink="/fil" style="margin-top:14px">{{ 'Retour au fil' | t }}</a>
      } @else if (post(); as p) {
        <app-post-card [post]="p" (changed)="post.set($event)" (removed)="router.navigate(['/fil'])" />
      } @else {
        <p class="muted">{{ 'Chargement…' | t }}</p>
      }
    </section>
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PostPage {
  readonly id = input.required<string>();
  private readonly api = inject(Api);
  protected readonly router = inject(Router);
  protected readonly post = signal<Post | null>(null);
  protected readonly error = signal<string | null>(null);

  constructor() {
    effect(() => {
      const id = this.id();
      untracked(() => {
        this.post.set(null);
        this.error.set(null);
        this.api.getPost(id).subscribe({ next: (p) => this.post.set(p), error: (e) => this.error.set(errorMessage(e)) });
      });
    });
  }

  protected back(): void {
    if (history.length > 1) history.back();
    else this.router.navigate(['/fil']);
  }
}
