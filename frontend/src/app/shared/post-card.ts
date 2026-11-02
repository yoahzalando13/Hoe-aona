import { ChangeDetectionStrategy, Component, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../core/api';
import { avatarTone, initials, kindIcon, relativeTime, verdictLabel } from '../core/format';
import { Comment, Post } from '../core/models';
import { MarkdownPipe } from '../core/markdown';
import { Icon } from './icon';
import { ScoreRing } from './score-ring';
import { PluralPipe, TPipe } from '../core/i18n';

@Component({
  selector: 'app-post-card',
  imports: [FormsModule, RouterLink, Icon, ScoreRing, MarkdownPipe, TPipe, PluralPipe],
  templateUrl: './post-card.html',
  styleUrl: './post-card.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PostCard {
  readonly post = input.required<Post>();
  /** Affiche les actions de modération (page d'administration). */
  readonly moderation = input(false);
  readonly changed = output<Post>();
  readonly removed = output<string>();

  private readonly api = inject(Api);

  protected readonly initials = initials;
  protected readonly avatarTone = avatarTone;
  protected readonly relativeTime = relativeTime;
  protected readonly verdictLabel = verdictLabel;
  protected readonly kindIcon = kindIcon;

  protected readonly expanded = signal(false);

  /** Article publié depuis une analyse : titres Markdown, rendu enrichi et repliable. */
  protected isArticle(body: string): boolean {
    return /^#\s/.test(body) || /\n##\s/.test(body);
  }

  protected isLong(body: string): boolean {
    return body.length > 700;
  }

  protected readonly showComments = signal(false);
  protected readonly comments = signal<Comment[] | null>(null);
  protected readonly editing = signal(false);
  protected readonly confirmDelete = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected draft = '';
  protected commentDraft = '';

  protected toggleLike(): void {
    const p = this.post();
    this.api.like(p.id, !p.liked).subscribe({
      next: (updated) => this.changed.emit(updated),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected toggleComments(): void {
    const open = !this.showComments();
    this.showComments.set(open);
    if (open && !this.comments()) {
      this.api.comments(this.post().id).subscribe({
        next: (list) => this.comments.set(list),
        error: (err) => this.error.set(errorMessage(err)),
      });
    }
  }

  protected sendComment(): void {
    const body = this.commentDraft.trim();
    if (!body) return;
    this.busy.set(true);
    this.api.addComment(this.post().id, body).subscribe({
      next: (list) => {
        this.comments.set(list);
        this.commentDraft = '';
        this.busy.set(false);
        this.changed.emit({ ...this.post(), comments_count: list.length });
      },
      error: (err) => { this.error.set(errorMessage(err)); this.busy.set(false); },
    });
  }

  protected removeComment(c: Comment): void {
    this.api.deleteComment(this.post().id, c.id).subscribe({
      next: () => {
        const list = (this.comments() ?? []).filter((x) => x.id !== c.id);
        this.comments.set(list);
        this.changed.emit({ ...this.post(), comments_count: list.length });
      },
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected startEdit(): void {
    this.draft = this.post().body;
    this.editing.set(true);
  }

  protected saveEdit(): void {
    const body = this.draft.trim();
    if (!body) return;
    this.busy.set(true);
    this.api.editPost(this.post().id, body).subscribe({
      next: (updated) => { this.editing.set(false); this.busy.set(false); this.changed.emit(updated); },
      error: (err) => { this.error.set(errorMessage(err)); this.busy.set(false); },
    });
  }

  protected remove(): void {
    this.api.deletePost(this.post().id).subscribe({
      next: () => this.removed.emit(this.post().id),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected toggleHidden(): void {
    const p = this.post();
    this.api.setHidden(p.id, !p.hidden).subscribe({
      next: (updated) => this.changed.emit(updated),
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected edited(p: Post): boolean {
    return new Date(p.updated_at).getTime() - new Date(p.created_at).getTime() > 60_000;
  }
}
