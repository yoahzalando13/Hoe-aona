import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { Auth } from './core/auth';
import { avatarTone, initials } from './core/format';
import { Icon } from './shared/icon';

interface NavItem { path: string; label: string; icon: string; }

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  templateUrl: './app.html',
  styleUrl: './app.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
  protected readonly auth = inject(Auth);
  protected readonly initials = initials;
  protected readonly avatarTone = avatarTone;

  protected readonly nav = computed<NavItem[]>(() => {
    const items: NavItem[] = [
      { path: '/fil', label: 'Fil', icon: 'feed' },
      { path: '/analyser', label: 'Analyser', icon: 'add' },
      { path: '/resultat', label: 'Résultat', icon: 'gauge' },
      { path: '/espace', label: 'Mon espace', icon: 'database' },
      { path: '/parametres', label: 'Paramètres', icon: 'settings' },
    ];
    if (this.auth.isAdmin()) items.push({ path: '/admin', label: 'Admin', icon: 'shield' });
    return items;
  });

  constructor() {
    this.auth.ensureLoaded();
  }
}
