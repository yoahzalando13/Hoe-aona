import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { formatScore, scoreTone, toneColor } from '../core/format';
import { TPipe } from '../core/i18n';

@Component({
  selector: 'app-score-ring',
  imports: [TPipe],
  template: `
    <svg [attr.width]="size()" [attr.height]="size()" viewBox="0 0 100 100" role="img"
         [attr.aria-label]="'Score {s} sur 10' | t: { s: label() }">
      <circle cx="50" cy="50" [attr.r]="r()" fill="none" stroke="var(--soft)" [attr.stroke-width]="stroke()" />
      <circle cx="50" cy="50" [attr.r]="r()" fill="none" [attr.stroke]="color()" [attr.stroke-width]="stroke()"
              stroke-linecap="round" [attr.stroke-dasharray]="dash()" transform="rotate(-90 50 50)" class="arc" />
    </svg>
    <div class="value" [style.color]="compact() ? color() : null">
      <span class="num" [class.compact]="compact()">{{ label() }}</span>
      @if (!compact()) { <span class="unit">/10</span> }
    </div>
    @if (caption()) { <span class="caption">{{ caption() }}</span> }
  `,
  styles: `
    :host { position: relative; display: inline-grid; place-items: center; }
    svg { display: block; }
    .arc { transition: stroke-dasharray .8s ease; }
    .value { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; }
    .num { font-size: calc(var(--ring-size, 160px) * 0.28); font-weight: 500; letter-spacing: -1.5px; }
    .num.compact { font-size: 12.5px; letter-spacing: 0; }
    .unit { font-size: calc(var(--ring-size, 160px) * 0.1); color: var(--ink3); margin-left: 3px; align-self: center; padding-top: 0.6em; }
    .caption { position: absolute; bottom: 24%; font-size: 12px; color: var(--ink3); }
  `,
  host: { '[style.--ring-size]': "size() + 'px'" },
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ScoreRing {
  readonly score = input<number | null>(null);
  readonly size = input(160);
  readonly compact = input(false);
  readonly caption = input<string>('');

  protected readonly stroke = computed(() => (this.compact() ? 10 : 8));
  protected readonly r = computed(() => 50 - this.stroke() / 2 - 1);
  protected readonly color = computed(() => toneColor(scoreTone(this.score())));
  protected readonly label = computed(() => formatScore(this.score()));
  protected readonly dash = computed(() => {
    const c = 2 * Math.PI * this.r();
    const v = Math.max(0, Math.min(10, this.score() ?? 0)) / 10;
    return `${(c * v).toFixed(1)} ${c.toFixed(1)}`;
  });
}
