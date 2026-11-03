import { ChangeDetectionStrategy, Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Api, errorMessage } from '../../core/api';
import { formatNumber } from '../../core/format';
import { PlatformActivity, RegionActivity, StatCatalog, StatIndicator, StatPoint, StatSeries, StatSeriesPair } from '../../core/models';
import { Icon } from '../../shared/icon';
import { TPipe, t } from '../../core/i18n';

interface ChartPoint { x: number; y: number; year: number; value: number; estimate: boolean; }

const W = 640;
const H = 240;
const PAD = { l: 56, r: 16, t: 14, b: 28 };

@Component({
  selector: 'app-stats-page',
  imports: [FormsModule, RouterLink, Icon, TPipe],
  templateUrl: './stats-page.html',
  styleUrl: './stats-page.css',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class StatsPage {
  private readonly api = inject(Api);
  protected readonly thisYear = new Date().getFullYear();
  protected readonly W = W;
  protected readonly H = H;
  protected readonly PAD = PAD;

  protected readonly catalog = signal<StatCatalog | null>(null);
  protected readonly dashboard = signal<StatSeries[] | null>(null);
  protected readonly dashError = signal<string | null>(null);

  protected readonly query = signal('');
  protected readonly theme = signal<string>('Tous');
  protected readonly indicator = signal('NY.GDP.MKTP.KD.ZG');
  protected readonly country = signal('MDG');
  protected readonly compareWith = signal<string[]>([]);

  protected readonly pair = signal<StatSeriesPair | null>(null);
  protected readonly loadingSeries = signal(false);
  protected readonly seriesError = signal<string | null>(null);
  protected readonly comparison = signal<StatSeries[] | null>(null);
  protected readonly loadingCompare = signal(false);
  protected readonly hover = signal<ChartPoint | null>(null);
  protected readonly hoverBar = signal<string | null>(null);
  protected readonly showTable = signal(false);
  protected readonly notice = signal<string | null>(null);

  /** Activité par région et contenus truqués (données fictives de démonstration, signalées comme telles). */
  protected readonly activity = signal<PlatformActivity | null>(null);
  protected readonly activityError = signal<string | null>(null);
  protected readonly regionSort = signal<'rate' | 'analyses' | 'deepfake'>('rate');
  protected readonly regions = computed(() => {
    const a = this.activity();
    if (!a) return { rows: [] as RegionActivity[], max: 1 };
    const key = { rate: 'rate_per_100k', analyses: 'analyses', deepfake: 'deepfake_rate' }[this.regionSort()] as keyof RegionActivity;
    const rows = [...a.regions].sort((x, y) => (y[key] as number) - (x[key] as number));
    return { rows, max: Math.max(...rows.map((r) => r[key] as number), 1), key };
  });
  protected readonly monthly = computed(() => {
    const months = this.activity()?.deepfake_monthly ?? [];
    const max = Math.max(...months.map((m) => m.rate), 1);
    return months.map((m, i) => {
      const [name, yy] = m.month.split(' ');
      // Nom du mois seul ; l'année sous le premier mois et sous janvier.
      return { ...m, name, year: i === 0 || name.startsWith('janv') ? `20${yy}` : '', h: (m.rate / max) * 100,
               last: i === months.length - 1 };
    });
  });
  protected regionValue(r: RegionActivity): number {
    return { rate: r.rate_per_100k, analyses: r.analyses, deepfake: r.deepfake_rate }[this.regionSort()];
  }
  protected int(n: number): string { return new Intl.NumberFormat(document.documentElement.lang || 'fr').format(n); }
  protected dec(n: number): string { return n.toLocaleString(document.documentElement.lang || 'fr', { maximumFractionDigits: 1 }); }

  protected readonly indicators = computed(() => {
    const cat = this.catalog();
    if (!cat) return [];
    const q = this.fold(this.query());
    return cat.indicators.filter((i) => (this.theme() === 'Tous' || i.theme === this.theme())
      && (!q || this.fold(`${i.label} ${i.unit} ${i.code}`).includes(q)));
  });
  protected readonly current = computed<StatIndicator | undefined>(() =>
    this.catalog()?.indicators.find((i) => i.code === this.indicator()));
  protected readonly countries = computed(() => this.catalog()?.countries ?? []);
  protected readonly countryName = computed(() => this.nameOf(this.country()));

  /** Série affichée : valeurs officielles Banque mondiale, prolongées par les estimations FMI plus récentes. */
  protected readonly points = computed<{ year: number; value: number; estimate: boolean; source: string }[]>(() => {
    const p = this.pair();
    if (!p?.worldbank.ok) return [];
    const wb = (p.worldbank.series ?? []).map((s) => ({ ...s, estimate: false, source: 'Banque mondiale' }));
    const lastWb = wb.length ? wb[wb.length - 1].year : 0;
    const imf = p.imf?.ok ? (p.imf.series ?? []).filter((s) => s.year > lastWb).map((s) => ({
      ...s, estimate: true, source: 'FMI',
    })) : [];
    return [...wb, ...imf];
  });

  protected readonly chart = computed(() => {
    const pts = this.points();
    if (pts.length < 2) return null;
    const ys = pts.map((p) => p.value);
    let min = Math.min(...ys);
    let max = Math.max(...ys);
    if (min > 0 && min / (max || 1) < 0.5) min = 0; // ancre à zéro quand l'écart le permet
    if (min === max) { min -= 1; max += 1; }
    const ticks = this.niceTicks(min, max, 4);
    const lo = ticks[0];
    const hi = ticks[ticks.length - 1];
    const x0 = pts[0].year;
    const x1 = pts[pts.length - 1].year;
    const sx = (y: number) => PAD.l + ((y - x0) / (x1 - x0 || 1)) * (W - PAD.l - PAD.r);
    const sy = (v: number) => PAD.t + (1 - (v - lo) / (hi - lo || 1)) * (H - PAD.t - PAD.b);
    const cp: ChartPoint[] = pts.map((p) => ({ x: sx(p.year), y: sy(p.value), year: p.year, value: p.value, estimate: p.estimate }));
    const official = cp.filter((p) => !p.estimate);
    const firstEst = cp.findIndex((p) => p.estimate);
    const estimate = firstEst > 0 ? cp.slice(firstEst - 1) : firstEst === 0 ? cp : [];
    const line = (list: ChartPoint[]) => list.map((p, i) => `${i ? 'L' : 'M'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join('');
    const step = Math.max(1, Math.ceil((x1 - x0) / 6));
    const xTicks: number[] = [];
    for (let y = x1; y >= x0; y -= step) xTicks.unshift(y);
    return {
      cp, official: line(official), estimate: line(estimate),
      yTicks: ticks.map((v) => ({ v, y: sy(v) })), xTicks: xTicks.map((y) => ({ year: y, x: sx(y) })),
      zeroY: lo < 0 && hi > 0 ? sy(0) : null,
    };
  });

  protected readonly latest = computed(() => {
    const pts = this.points();
    const official = [...pts].reverse().find((p) => !p.estimate);
    const est = pts.length && pts[pts.length - 1].estimate ? pts[pts.length - 1] : null;
    return { official, est };
  });

  protected readonly bars = computed(() => {
    const list = (this.comparison() ?? []).filter((c) => c.ok && c.latest_value != null);
    const max = Math.max(...list.map((c) => Math.abs(c.latest_value!)), 0) || 1;
    const hasNeg = list.some((c) => c.latest_value! < 0);
    return {
      hasNeg,
      items: [...list].sort((a, b) => b.latest_value! - a.latest_value!).map((c) => ({
        ...c, pct: (Math.abs(c.latest_value!) / max) * (hasNeg ? 50 : 100), neg: c.latest_value! < 0,
      })),
      missing: (this.comparison() ?? []).filter((c) => !c.ok || c.latest_value == null).map((c) => c.country).join(', '),
    };
  });

  constructor() {
    this.api.statsCatalog().subscribe({
      next: (cat) => {
        this.catalog.set(cat);
        this.compareWith.set(cat.neighbours);
      },
      error: (err) => this.seriesError.set(errorMessage(err)),
    });
    this.api.statsActivity().subscribe({
      next: (a) => this.activity.set(a),
      error: (err) => this.activityError.set(errorMessage(err)),
    });
    this.api.statsMadagascar().subscribe({
      next: (items) => this.dashboard.set(items),
      error: (err) => this.dashError.set(errorMessage(err)),
    });
    effect(() => {
      const ind = this.indicator();
      const c = this.country();
      untracked(() => this.loadSeries(ind, c));
    });
    effect(() => {
      const ind = this.indicator();
      const list = this.compareWith();
      if (!list.length) return;
      untracked(() => this.loadCompare(ind, list));
    });
  }

  private loadSeries(indicator: string, country: string): void {
    this.loadingSeries.set(true);
    this.seriesError.set(null);
    this.hover.set(null);
    this.api.statsSeries(indicator, country).subscribe({
      next: (p) => { this.pair.set(p); this.loadingSeries.set(false); },
      error: (err) => { this.pair.set(null); this.seriesError.set(errorMessage(err)); this.loadingSeries.set(false); },
    });
  }

  private loadCompare(indicator: string, countries: string[]): void {
    this.loadingCompare.set(true);
    this.api.statsCompare(indicator, countries).subscribe({
      next: (list) => { this.comparison.set(list); this.loadingCompare.set(false); },
      error: () => { this.comparison.set(null); this.loadingCompare.set(false); },
    });
  }

  protected pick(code: string): void {
    this.indicator.set(code);
    this.country.set('MDG');
    document.getElementById('explorer')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  protected toggleCompare(code: string): void {
    this.compareWith.update((list) => list.includes(code) ? list.filter((c) => c !== code)
      : list.length >= 10 ? list : [...list, code]);
  }

  protected nameOf(code: string): string {
    return this.countries().find((c) => c.code === code)?.name ?? code;
  }

  // ---------- Formatage ----------
  protected fmt(value: number | null | undefined, unit = ''): string {
    if (value == null) return '—';
    const abs = Math.abs(value);
    if (unit.startsWith('US$') || unit === 'habitants') {
      if (abs >= 1e9) return `${(value / 1e9).toFixed(1).replace('.', ',')} Md`;
      if (abs >= 1e6) return `${(value / 1e6).toFixed(1).replace('.', ',')} M`;
    }
    return formatNumber(Math.round(value * 10) / 10);
  }

  protected shortUnit(unit = ''): string {
    if (unit.startsWith('US$')) return 'US$';
    if (unit === 'habitants') return 'hab.';
    if (unit.startsWith('%')) return '%';
    return unit;
  }

  protected age(year: number | null | undefined): number {
    return year ? this.thisYear - year : 99;
  }

  protected spark(series: StatPoint[] | undefined): string {
    const pts = series ?? [];
    if (pts.length < 2) return '';
    const vs = pts.map((p) => p.value);
    const min = Math.min(...vs);
    const span = Math.max(...vs) - min || 1;
    return pts.map((p, i) => `${((i / (pts.length - 1)) * 96 + 2).toFixed(1)},${(26 - ((p.value - min) / span) * 22).toFixed(1)}`).join(' ');
  }

  protected trend(series: StatPoint[] | undefined): 'up' | 'down' | 'flat' {
    const pts = series ?? [];
    if (pts.length < 2) return 'flat';
    const d = pts[pts.length - 1].value - pts[pts.length - 2].value;
    const rel = Math.abs(d) / (Math.abs(pts[pts.length - 2].value) || 1);
    return rel < 0.005 ? 'flat' : d > 0 ? 'up' : 'down';
  }

  // ---------- Graphique : survol et clavier ----------
  protected onMove(event: PointerEvent, svg: Element): void {
    const c = this.chart();
    if (!c) return;
    const rect = svg.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * W;
    let best = c.cp[0];
    for (const p of c.cp) if (Math.abs(p.x - x) < Math.abs(best.x - x)) best = p;
    this.hover.set(best);
  }

  protected onKey(event: KeyboardEvent): void {
    const c = this.chart();
    if (!c || !['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    const h = this.hover();
    const i = h ? c.cp.findIndex((p) => p.year === h.year) : c.cp.length;
    const next = Math.min(c.cp.length - 1, Math.max(0, i + (event.key === 'ArrowRight' ? 1 : -1)));
    this.hover.set(c.cp[next]);
  }

  protected tipLeft(p: ChartPoint): number {
    return Math.min(85, Math.max(15, (p.x / W) * 100));
  }

  // ---------- Citation pour les journalistes ----------
  protected async cite(): Promise<void> {
    const p = this.pair()?.worldbank;
    const { official, est } = this.latest();
    if (!p?.ok || !official) return;
    let text = `${p.indicator_name}, ${p.country} : ${this.fmt(official.value, p.unit)} (${p.unit}) en ${official.year} `
      + `— Banque mondiale, ${p.source_url}`;
    const imf = this.pair()?.imf;
    if (est && imf?.ok) text += `. Estimation FMI ${est.year} : ${this.fmt(est.value, p.unit)} — ${imf.source_url}`;
    try {
      await navigator.clipboard.writeText(text + '.');
      this.flash(t('Chiffre copié avec sa source'));
    } catch {
      this.flash(t('Copie impossible'));
    }
  }

  private flash(message: string): void {
    this.notice.set(message);
    setTimeout(() => this.notice.set(null), 2400);
  }

  private fold(s: string): string {
    return s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }

  private niceTicks(min: number, max: number, count: number): number[] {
    const raw = (max - min) / count;
    const mag = 10 ** Math.floor(Math.log10(raw));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
    const lo = Math.floor(min / step) * step;
    const hi = Math.ceil(max / step) * step;
    const out: number[] = [];
    for (let v = lo; v <= hi + step / 2; v += step) out.push(Math.round(v * 1e6) / 1e6);
    return out;
  }
}
