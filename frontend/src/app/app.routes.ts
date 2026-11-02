import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'analyser' },
  { path: 'analyser', title: 'Analyser — Hoe-aona?', loadComponent: () => import('./pages/analyze/analyze-page').then((m) => m.AnalyzePage) },
  { path: 'resultat', title: 'Résultat — Hoe-aona?', loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage) },
  { path: 'resultat/:id', title: 'Résultat — Hoe-aona?', loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage) },
  { path: 'historique', title: 'Historique — Hoe-aona?', loadComponent: () => import('./pages/history/history-page').then((m) => m.HistoryPage) },
  { path: 'parametres', title: 'Paramètres — Hoe-aona?', loadComponent: () => import('./pages/settings/settings-page').then((m) => m.SettingsPage) },
  { path: '**', redirectTo: 'analyser' },
];
