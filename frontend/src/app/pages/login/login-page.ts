import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { Auth } from '../../core/auth';
import { AuthConfig } from '../../core/models';

@Component({
  selector: 'app-login-page',
  imports: [FormsModule],
  templateUrl: './login-page.html',
  styleUrl: './login-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LoginPage {
  /** URL demandée avant la redirection vers la connexion. */
  readonly retour = input<string>();

  private readonly api = inject(Api);
  private readonly auth = inject(Auth);
  private readonly router = inject(Router);

  protected readonly mode = signal<'login' | 'register'>('login');
  protected readonly config = signal<AuthConfig | null>(null);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);

  protected email = '';
  protected password = '';
  protected displayName = '';
  protected organization = '';

  constructor() {
    this.api.authConfig().subscribe({
      next: (c) => {
        this.config.set(c);
        if (!c.has_users) this.mode.set('register');
      },
      error: (err) => this.error.set(errorMessage(err)),
    });
  }

  protected switchTo(mode: 'login' | 'register'): void {
    this.mode.set(mode);
    this.error.set(null);
  }

  protected submit(): void {
    this.busy.set(true);
    this.error.set(null);
    const req = this.mode() === 'login'
      ? this.auth.login(this.email.trim(), this.password)
      : this.auth.register({
          email: this.email.trim(), password: this.password,
          display_name: this.displayName.trim(), organization: this.organization.trim(),
        });
    req.subscribe({
      next: () => {
        const target = this.retour();
        this.router.navigateByUrl(target && target.startsWith('/') && !target.startsWith('//') ? target : '/fil');
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.busy.set(false);
      },
    });
  }
}
