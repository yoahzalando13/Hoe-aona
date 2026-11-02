import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { forkJoin } from 'rxjs';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { Auth } from '../../core/auth';
import { Health, Preferences } from '../../core/models';
import { Icon } from '../../shared/icon';
import { LANG, LANGS, Lang, TPipe, applyLang, t } from '../../core/i18n';

type WeightKey = 'weight_source' | 'weight_veracity' | 'weight_ai';

const COUNTRIES = [
  { code: 'MDG', name: t('Madagascar') }, { code: 'COM', name: t('Comores') }, { code: 'MUS', name: t('Maurice') },
  { code: 'SYC', name: t('Seychelles') }, { code: 'MOZ', name: t('Mozambique') }, { code: 'ZAF', name: t('Afrique du Sud') },
  { code: 'SEN', name: t('Sénégal') }, { code: 'CIV', name: t('Côte d’Ivoire') }, { code: 'CMR', name: t('Cameroun') },
  { code: 'COD', name: t('RD Congo') }, { code: 'MAR', name: t('Maroc') }, { code: 'FRA', name: t('France') },
  { code: 'BEL', name: t('Belgique') }, { code: 'CAN', name: t('Canada') }, { code: 'USA', name: t('États-Unis') },
  { code: 'WLD', name: t('Monde') },
];

@Component({
  selector: 'app-settings-page',
  imports: [FormsModule, RouterLink, Icon, TPipe],
  templateUrl: './settings-page.html',
  styleUrl: './settings-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPage {
  private readonly api = inject(Api);
  protected readonly auth = inject(Auth);

  protected readonly countries = COUNTRIES;
  protected readonly weights: { key: WeightKey; label: string; icon: string; tone: string }[] = [
    { key: 'weight_source', label: t('Source'), icon: 'globe', tone: 'tone-blue' },
    { key: 'weight_veracity', label: t('Véracité des données'), icon: 'verify', tone: 'tone-amber' },
    { key: 'weight_ai', label: t('Fait par IA'), icon: 'robot', tone: 'tone-purple' },
  ];

  protected readonly langs = LANGS;
  protected readonly currentLang = LANG;
  protected readonly prefs = signal<Preferences | null>(null);
  protected readonly saved = signal<string>('');
  protected readonly health = signal<Health | null>(null);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);

  protected readonly weightTotal = computed(() => {
    const p = this.prefs();
    return p ? p.weight_source + p.weight_veracity + p.weight_ai : 0;
  });
  /** La langue de l'interface change à l'enregistrement (la page se recharge). */
  protected readonly langPending = computed(() => {
    const ui = this.prefs()?.ui_language;
    return !!ui && ui !== LANG;
  });
  protected readonly dirty = computed(() => !!this.prefs() && JSON.stringify(this.prefs()) !== this.saved());
  protected readonly missingKeys = computed(
    () => (this.health()?.providers ?? []).filter((p) => p.requires_key && !p.configured).length,
  );
  protected readonly hasLlm = computed(() =>
    (this.health()?.providers ?? []).some((p) => (p.key === 'gemini' || p.key === 'groq') && p.configured),
  );

  constructor() {
    forkJoin({ prefs: this.api.getSettings(), health: this.api.health() }).subscribe({
      next: ({ prefs, health }) => {
        this.prefs.set(prefs);
        this.saved.set(JSON.stringify(prefs));
        this.health.set(health);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.loading.set(false);
      },
    });
  }

  /** Changer la langue de l'interface entraîne aussi celle du rapport, si les deux étaient identiques. */
  protected setUiLanguage(lang: Lang): void {
    this.prefs.update((p) => {
      if (!p) return p;
      const previous = p.ui_language ?? LANG;
      return { ...p, ui_language: lang, report_language: p.report_language === previous ? lang : p.report_language };
    });
  }

  protected update<K extends keyof Preferences>(key: K, value: Preferences[K]): void {
    this.prefs.update((p) => (p ? { ...p, [key]: value } : p));
  }

  /** Part réelle d'un critère dans le score global, après normalisation. */
  protected share(key: WeightKey): number {
    const p = this.prefs();
    const total = this.weightTotal();
    return p && total ? Math.round((p[key] / total) * 100) : 0;
  }

  protected resetWeights(): void {
    this.prefs.update((p) => (p ? { ...p, weight_source: 40, weight_veracity: 40, weight_ai: 20 } : p));
  }

  protected save(): void {
    const p = this.prefs();
    if (!p) return;
    if (this.weightTotal() === 0) {
      this.error.set(t('Au moins un critère doit avoir un poids supérieur à zéro.'));
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    this.api.saveSettings(p).subscribe({
      next: (stored) => {
        this.prefs.set(stored);
        this.saved.set(JSON.stringify(stored));
        this.saving.set(false);
        this.flash(t('Paramètres enregistrés'));
        applyLang(stored.ui_language);
      },
      error: (err) => {
        this.error.set(errorMessage(err));
        this.saving.set(false);
      },
    });
  }

  protected cancel(): void {
    const saved = this.saved();
    if (saved) this.prefs.set(JSON.parse(saved) as Preferences);
  }

  private flash(message: string): void {
    this.notice.set(message);
    setTimeout(() => this.notice.set(null), 2400);
  }
}
