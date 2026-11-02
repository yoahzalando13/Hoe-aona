import { Routes } from '@angular/router';
import { adminGuard, authGuard, guestGuard } from './core/auth';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'fil' },
  { path: 'connexion', title: 'Connexion — Hoe-aona?', canActivate: [guestGuard], loadComponent: () => import('./pages/login/login-page').then((m) => m.LoginPage) },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      { path: 'fil', title: 'Fil média — Hoe-aona?', loadComponent: () => import('./pages/feed/feed-page').then((m) => m.FeedPage) },
      { path: 'analyser', title: 'Analyser — Hoe-aona?', loadComponent: () => import('./pages/analyze/analyze-page').then((m) => m.AnalyzePage) },
      { path: 'resultat', title: 'Résultat — Hoe-aona?', loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage) },
      { path: 'resultat/:id', title: 'Résultat — Hoe-aona?', loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage) },
      { path: 'espace', title: 'Mon espace — Hoe-aona?', loadComponent: () => import('./pages/workspace/workspace-page').then((m) => m.WorkspacePage) },
      { path: 'historique', title: 'Historique — Hoe-aona?', loadComponent: () => import('./pages/history/history-page').then((m) => m.HistoryPage) },
      { path: 'publication/:id', title: 'Publication — Hoe-aona?', loadComponent: () => import('./pages/post/post-page').then((m) => m.PostPage) },
      { path: 'sources', title: 'Sources officielles — Hoe-aona?', loadComponent: () => import('./pages/sources/sources-page').then((m) => m.SourcesPage) },
      { path: 'profil/:id', title: 'Profil — Hoe-aona?', loadComponent: () => import('./pages/profile/profile-page').then((m) => m.ProfilePage) },
      { path: 'parametres', title: 'Paramètres — Hoe-aona?', loadComponent: () => import('./pages/settings/settings-page').then((m) => m.SettingsPage) },
      { path: 'admin', title: 'Administration — Hoe-aona?', canActivate: [adminGuard], loadComponent: () => import('./pages/admin/admin-page').then((m) => m.AdminPage) },
    ],
  },
  { path: '**', redirectTo: 'fil' },
];
