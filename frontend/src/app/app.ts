import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs';
import { Auth } from './core/auth';
import { avatarTone, initials } from './core/format';
import { Icon } from './shared/icon';
import { TPipe, t } from './core/i18n';

/** `primary` : visible dans la barre du bas sur téléphone ; les autres passent dans « Plus ». */
interface NavItem { path: string; label: string; icon: string; primary: boolean; }

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon, TPipe],
  templateUrl: './app.html',
  styleUrl: './app.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  protected readonly auth = inject(Auth);
  private readonly router = inject(Router);
  protected readonly initials = initials;
  protected readonly avatarTone = avatarTone;
  protected readonly moreOpen = signal(false);

  protected readonly nav = computed<NavItem[]>(() => {
    // Lecteur : uniquement le fil et son profil (le menu « Plus » garde la déconnexion sur téléphone).
    if (this.auth.isReader()) {
      const me = this.auth.user();
      return [
        { path: '/fil', label: t('Actualités'), icon: 'feed', primary: true },
        ...(me ? [{ path: `/profil/${me.id}`, label: t('Mon profil'), icon: 'users', primary: true }] : []),
      ];
    }
    const items: NavItem[] = [
      { path: '/fil', label: t('Fil'), icon: 'feed', primary: true },
      { path: '/analyser', label: t('Analyser'), icon: 'add', primary: true },
      { path: '/resultat', label: t('Résultat'), icon: 'gauge', primary: true },
      { path: '/statistiques', label: t('Statistiques'), icon: 'chart', primary: true },
      { path: '/sources-officielles', label: t('Sources officielles'), icon: 'users', primary: false },
      { path: '/espace', label: t('Mon espace'), icon: 'database', primary: false },
      { path: '/parametres', label: t('Paramètres'), icon: 'settings', primary: false },
    ];
    if (this.auth.isAdmin()) items.push({ path: '/admin', label: t('Admin'), icon: 'shield', primary: false });
    return items;
  });
  protected readonly secondary = computed(() => this.nav().filter((i) => !i.primary));

  private readonly url = toSignal(
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd), map(() => this.router.url)),
    { initialValue: this.router.url },
  );
  /** Le bouton « Plus » s'allume quand la page courante est l'une des entrées secondaires. */
  protected readonly secondaryActive = computed(() => {
    const url = this.url();
    return this.secondary().some((i) => url.startsWith(i.path)) || url.startsWith('/profil');
  });

  constructor() {
    this.auth.ensureLoaded();
  }
}
