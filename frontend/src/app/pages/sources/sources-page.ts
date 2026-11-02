import { ChangeDetectionStrategy, Component, DestroyRef, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Api, errorMessage } from '../../core/api';
import { Auth } from '../../core/auth';
import { OfficialSource, OfficialSourceIn } from '../../core/models';
import { Icon } from '../../shared/icon';
import { TPipe, t } from '../../core/i18n';

interface Draft extends Omit<OfficialSourceIn, 'topics'> { topics: string; }

/** Icône par catégorie d'institution (catégories saisies librement : repli sur « globe »). */
const CATEGORY_ICON: Record<string, string> = {
  'Statistiques officielles': 'chart', 'Institution monétaire': 'database', 'Ministère': 'layers',
  'Institution': 'shield', 'Parlement': 'users', 'Gestion des risques': 'alert', 'Météorologie': 'globe',
  'Lutte contre la corruption': 'verify', 'Administration': 'document', 'Entreprise publique': 'sparkle',
  'Institution internationale': 'globe',
};

/** Portails de données ouverts, vérifiés joignables le 3 novembre 2026. */
const PORTALS = [
  { name: 'INSTAT Madagascar', desc: 'Recensements, prix, enquêtes auprès des ménages', url: 'https://www.instat.mg', icon: 'chart' },
  { name: 'Banque centrale (BFM)', desc: 'Taux de change, inflation, statistiques monétaires', url: 'https://banque-centrale.mg', icon: 'database' },
  { name: 'Banque mondiale · Madagascar', desc: 'Indicateurs de développement, séries longues', url: 'https://data.worldbank.org/country/madagascar', icon: 'globe' },
  { name: 'FMI · Madagascar', desc: 'Prévisions économiques (World Economic Outlook)', url: 'https://www.imf.org/external/datamapper/profile/MDG', icon: 'chart' },
  { name: 'HDX · Madagascar', desc: 'Données humanitaires : cyclones, sécurité alimentaire', url: 'https://data.humdata.org/group/mdg', icon: 'alert' },
];

const EMPTY: Draft = {
  name: '', acronym: '', category: '', website: '', email: '', phone: '', address: '', notes: '', topics: '',
  verified_at: null, active: true,
};

@Component({
  selector: 'app-sources-page',
  imports: [DatePipe, NgTemplateOutlet, FormsModule, RouterLink, Icon, TPipe],
  templateUrl: './sources-page.html',
  styleUrl: './sources-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SourcesPage {
  private readonly api = inject(Api);
  protected readonly auth = inject(Auth);

  protected readonly sources = signal<OfficialSource[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);
  protected readonly query = signal('');
  protected readonly editId = signal<string | 'new' | null>(null);
  protected readonly confirmId = signal<string | null>(null);
  protected readonly saving = signal(false);
  protected draft: Draft = { ...EMPTY };
  protected readonly category = signal<string | null>(null);
  protected readonly portals = PORTALS;
  private readonly today = Date.now();

  /** Catégories présentes, avec leur nombre de sources, pour les filtres. */
  protected readonly categories = computed(() => {
    const counts = new Map<string, number>();
    for (const s of this.sources()) {
      const c = s.category || t('Autres');
      counts.set(c, (counts.get(c) ?? 0) + 1);
    }
    return [...counts.entries()].map(([label, n]) => ({ label, n }));
  });

  protected readonly visibleGroups = computed(() => {
    const c = this.category();
    return c ? this.groups().filter((g) => g.label === c) : this.groups();
  });

  protected readonly counts = computed(() => {
    const list = this.sources();
    return {
      total: list.length,
      reachable: list.filter((s) => s.phone || s.email).length,
      stale: list.filter((s) => this.stale(s)).length,
    };
  });

  protected readonly groups = computed(() => {
    const out: { label: string; items: OfficialSource[] }[] = [];
    for (const s of this.sources()) {
      const label = s.category || t('Autres');
      const g = out.find((x) => x.label === label);
      if (g) g.items.push(s);
      else out.push({ label, items: [s] });
    }
    return out;
  });

  private debounce: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.load();
    inject(DestroyRef).onDestroy(() => { if (this.debounce) clearTimeout(this.debounce); });
  }

  protected load(): void {
    this.loading.set(true);
    this.api.sources(this.query().trim(), this.auth.isAdmin()).subscribe({
      next: (list) => { this.sources.set(list); this.loading.set(false); },
      error: (e) => { this.error.set(errorMessage(e)); this.loading.set(false); },
    });
  }

  protected onQuery(v: string): void {
    this.query.set(v);
    if (this.debounce) clearTimeout(this.debounce);
    this.debounce = setTimeout(() => this.load(), 300);
  }

  protected startNew(): void {
    this.draft = { ...EMPTY, verified_at: new Date().toISOString().slice(0, 10) };
    this.editId.set('new');
  }

  protected edit(s: OfficialSource): void {
    this.draft = { ...s, topics: s.topics.join(', ') };
    this.editId.set(s.id);
  }

  protected save(): void {
    const id = this.editId();
    const payload: OfficialSourceIn = {
      ...this.draft, verified_at: this.draft.verified_at || null,
      topics: this.draft.topics.split(',').map((t) => t.trim()).filter(Boolean),
    };
    this.saving.set(true);
    this.error.set(null);
    const req = id === 'new' ? this.api.createSource(payload) : this.api.updateSource(id!, payload);
    req.subscribe({
      next: () => { this.saving.set(false); this.editId.set(null); this.load(); this.flash(t('Source enregistrée')); },
      error: (e) => { this.error.set(errorMessage(e)); this.saving.set(false); },
    });
  }

  protected remove(s: OfficialSource): void {
    this.api.deleteSource(s.id).subscribe({
      next: () => { this.confirmId.set(null); this.sources.update((l) => l.filter((x) => x.id !== s.id)); this.flash(t('Source supprimée')); },
      error: (e) => this.error.set(errorMessage(e)),
    });
  }

  protected icon(category: string): string {
    return CATEGORY_ICON[category] ?? 'globe';
  }

  protected host(url: string): string {
    return url.replace(/^https?:\/\//, '').replace(/^www\./, '').replace(/\/$/, '');
  }

  /** Coordonnées à revérifier : jamais vérifiées, ou vérifiées il y a plus d'un an. */
  protected stale(s: OfficialSource): boolean {
    return !s.verified_at || this.today - new Date(s.verified_at).getTime() > 365 * 86_400_000;
  }

  protected async copy(s: OfficialSource): Promise<void> {
    const lines = [s.acronym ? `${s.name} (${s.acronym})` : s.name, s.website, s.phone && `Tél. : ${s.phone}`,
      s.email && `E-mail : ${s.email}`, s.address].filter(Boolean);
    try {
      await navigator.clipboard.writeText(lines.join('\n'));
      this.flash(t('Coordonnées copiées'));
    } catch {
      this.flash(t('Copie impossible'));
    }
  }

  protected tel(phone: string): { label: string; href: string }[] {
    return phone.split('/').map((p) => p.trim()).filter(Boolean).map((label) => ({
      label, href: 'tel:' + label.replace(/\(.*?\)/g, '').replace(/[^\d+]/g, ''),
    }));
  }

  private flash(message: string): void {
    this.notice.set(message);
    setTimeout(() => this.notice.set(null), 2400);
  }
}
