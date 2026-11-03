import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { formatScore, scoreTone, toneColor } from '../core/format';
import { TPipe, t } from '../core/i18n';

/**
 * Score sur 10 lu comme une règle graduée : grand chiffre en serif, curseur posé sur une échelle 0 à 10.
 * En version compacte (listes), le chiffre et un trait proportionnel suffisent.
 * Le sélecteur garde son nom historique pour ne pas toucher aux gabarits.
 */
@Component({
  selector: 'app-score-ring',
  imports: [TPipe],
  template: `
    @if (compact()) {
      <span class="c-num" [style.color]="color()">{{ label() }}</span>
      <span class="c-track" aria-hidden="true"><i [style.width.%]="pct()" [style.background]="color()"></i></span>
    } @else {
      @if (caption()) { <span class="caption">{{ caption() | t }}</span> }
      <span class="figure"><span class="num" [style.color]="color()">{{ label() }}</span><span class="unit">/10</span></span>
      <svg class="ruler" viewBox="0 0 104 16" aria-hidden="true">
        <rect x="2" y="9" width="100" height="3" class="rail" />
        <rect x="2" y="9" [attr.width]="pct()" height="3" [attr.fill]="color()" class="fill" />
        @for (t of ticks; track t) {
          <line [attr.x1]="2 + t * 10" [attr.x2]="2 + t * 10" [attr.y1]="t % 5 === 0 ? 5 : 7.5" y2="12" class="tick" />
        }
        <path [attr.d]="marker()" [attr.fill]="color()" />
      </svg>
      <span class="ends" aria-hidden="true"><span>0</span><span>5</span><span>10</span></span>
    }
  `,
  styles: `
    :host { display: inline-flex; flex-direction: column; align-items: stretch; width: var(--ring-size, 160px); }
    .caption { font-size: 11px; font-weight: 600; letter-spacing: .09em; text-transform: uppercase; color: var(--ink2); text-align: left; }
    .figure { display: flex; align-items: baseline; gap: 4px; margin: 2px 0 6px; }
    .num {
      font-family: var(--serif); font-weight: 500; line-height: .95; letter-spacing: -1px;
      font-size: calc(var(--ring-size, 160px) * 0.42); font-variant-numeric: lining-nums tabular-nums;
    }
    .unit { font-family: var(--serif); font-size: calc(var(--ring-size, 160px) * 0.13); color: var(--ink3); }
    .ruler { display: block; width: 100%; height: auto; overflow: visible; }
    .rail { fill: var(--soft); }
    .fill { transition: width .8s ease; }
    .tick { stroke: var(--ink3); stroke-width: .6; }
    .ends { display: flex; justify-content: space-between; font-size: 10.5px; color: var(--ink3); font-variant-numeric: tabular-nums; padding: 0 0 0 1px; }
    .c-num { font-family: var(--serif); font-size: calc(var(--ring-size, 44px) * 0.46); font-weight: 600; line-height: 1; font-variant-numeric: lining-nums tabular-nums; text-align: right; }
    .c-track { display: block; height: 2px; margin-top: 4px; background: var(--line); }
    .c-track i { display: block; height: 100%; }
  `,
  host: {
    role: 'img',
    '[attr.aria-label]': 'ariaLabel()',
    '[style.--ring-size]': "size() + 'px'",
  },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScoreRing {
  readonly score = input<number | null>(null);
  readonly size = input(160);
  readonly compact = input(false);
  readonly caption = input<string>('');

  protected readonly ticks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
  protected readonly color = computed(() => toneColor(scoreTone(this.score())));
  protected readonly label = computed(() => formatScore(this.score()));
  protected readonly ariaLabel = computed(() => t('Score {s} sur 10', { s: this.label() }));
  protected readonly pct = computed(() => Math.max(0, Math.min(10, this.score() ?? 0)) * 10);
  /** Curseur triangulaire posé au-dessus du rail, à la position du score. */
  protected readonly marker = computed(() => {
    const x = 2 + this.pct();
    return `M${x - 3} 2 L${x + 3} 2 L${x} 7 Z`;
  });
}
