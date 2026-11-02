import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { Observable, catchError, firstValueFrom, of, tap, throwError } from 'rxjs';
import { Api } from './api';
import { applyLang } from './i18n';
import { User } from './models';

/** Compte connecté, partagé par toute l'application. */
@Injectable({ providedIn: 'root' })
export class Auth {
  private readonly api = inject(Api);
  private readonly router = inject(Router);
  private loaded: Promise<User | null> | null = null;

  readonly user = signal<User | null>(null);
  readonly isAdmin = computed(() => this.user()?.role === 'admin');

  /** Charge la session une seule fois (cookie HttpOnly côté serveur). */
  ensureLoaded(): Promise<User | null> {
    this.loaded ??= firstValueFrom(
      this.api.me().pipe(
        tap((u) => { this.user.set(u); this.syncLang(); }),
        catchError(() => of(null)),
      ),
    );
    return this.loaded;
  }

  login(email: string, password: string): Observable<User> {
    return this.api.login(email, password).pipe(tap((u) => this.set(u)));
  }

  register(payload: { email: string; password: string; display_name: string; organization: string }): Observable<User> {
    return this.api.register(payload).pipe(tap((u) => this.set(u)));
  }

  set(user: User): void {
    this.user.set(user);
    this.loaded = Promise.resolve(user);
    this.syncLang();
  }

  /** La langue choisie dans les paramètres du compte s'applique sur tous les appareils. */
  private syncLang(): void {
    this.api.getSettings().pipe(catchError(() => of(null))).subscribe((prefs) => applyLang(prefs?.ui_language));
  }

  logout(): void {
    this.api.logout().pipe(catchError(() => of(null))).subscribe(() => this.expire());
  }

  /** Session perdue : on revient à l'écran de connexion. */
  expire(): void {
    this.user.set(null);
    this.loaded = Promise.resolve(null);
    if (!this.router.url.startsWith('/connexion')) {
      this.router.navigate(['/connexion'], { queryParams: { retour: this.router.url === '/' ? null : this.router.url } });
    }
  }
}

export const authGuard: CanActivateFn = async (_route, state) => {
  const auth = inject(Auth);
  const router = inject(Router);
  return (await auth.ensureLoaded()) ? true : router.createUrlTree(['/connexion'], { queryParams: { retour: state.url } });
};

export const adminGuard: CanActivateFn = async () => {
  const auth = inject(Auth);
  const router = inject(Router);
  const user = await auth.ensureLoaded();
  return user?.role === 'admin' ? true : router.createUrlTree(['/fil']);
};

export const guestGuard: CanActivateFn = async () => {
  const auth = inject(Auth);
  const router = inject(Router);
  return (await auth.ensureLoaded()) ? router.createUrlTree(['/fil']) : true;
};

/** Toute réponse 401 hors /api/auth renvoie vers la connexion. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(Auth);
  return next(req).pipe(
    catchError((err: unknown) => {
      if (err instanceof HttpErrorResponse && err.status === 401 && !req.url.includes('/api/auth/')) auth.expire();
      return throwError(() => err);
    }),
  );
};
