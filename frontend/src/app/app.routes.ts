import { Routes } from '@angular/router';
import { adminGuard, authGuard, guestGuard, staffGuard } from './core/auth';
import { t } from './core/i18n';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'fil' },
  { path: 'connexion', title: t('Connexion') + ' — Hoe-aona?', canActivate: [guestGuard], loadComponent: () => import('./pages/login/login-page').then((m) => m.LoginPage) },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      { path: 'fil', title: t('Fil média') + ' — Hoe-aona?', loadComponent: () => import('./pages/feed/feed-page').then((m) => m.FeedPage) },
      { path: 'analyser', canActivate: [staffGuard], title: t('Analyser') + ' — Hoe-aona?', loadComponent: () => import('./pages/analyze/analyze-page').then((m) => m.AnalyzePage) },
      { path: 'resultat', canActivate: [staffGuard], title: t('Résultat') + ' — Hoe-aona?', loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage) },
      { path: 'resultat/:id', canActivate: [staffGuard], title: t('Résultat') + ' — Hoe-aona?', loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage) },
      { path: 'espace', canActivate: [staffGuard], title: t('Mon espace') + ' — Hoe-aona?', loadComponent: () => import('./pages/workspace/workspace-page').then((m) => m.WorkspacePage) },
      { path: 'historique', canActivate: [staffGuard], title: t('Historique') + ' — Hoe-aona?', loadComponent: () => import('./pages/history/history-page').then((m) => m.HistoryPage) },
      { path: 'publication/:id', title: t('Publication') + ' — Hoe-aona?', loadComponent: () => import('./pages/post/post-page').then((m) => m.PostPage) },
      { path: 'statistiques', canActivate: [staffGuard], title: t('Statistiques') + ' — Hoe-aona?', loadComponent: () => import('./pages/stats/stats-page').then((m) => m.StatsPage) },
      { path: 'sources-officielles', canActivate: [staffGuard], title: t('Sources officielles') + ' — Hoe-aona?', loadComponent: () => import('./pages/sources/sources-page').then((m) => m.SourcesPage) },
      { path: 'sources', pathMatch: 'full', redirectTo: 'sources-officielles' },
      { path: 'profil/:id', title: t('Profil') + ' — Hoe-aona?', loadComponent: () => import('./pages/profile/profile-page').then((m) => m.ProfilePage) },
      { path: 'parametres', canActivate: [staffGuard], title: t('Paramètres') + ' — Hoe-aona?', loadComponent: () => import('./pages/settings/settings-page').then((m) => m.SettingsPage) },
      { path: 'admin', title: t('Administration') + ' — Hoe-aona?', canActivate: [adminGuard], loadComponent: () => import('./pages/admin/admin-page').then((m) => m.AdminPage) },
    ],
  },
  { path: '**', redirectTo: 'fil' },
];
