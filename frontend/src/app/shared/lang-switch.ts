import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { LANG, LANGS, Lang, TPipe, setLang } from '../core/i18n';

/**
 * Choix de la langue avant connexion (écran de connexion). Une fois connecté, la langue se règle dans
 * Paramètres → Langue et s'enregistre dans le compte.
 */
@Component({
  selector: 'app-lang-switch',
  imports: [TPipe],
  template: `
    <div class="lang" role="group" [attr.aria-label]="'Langue de l’interface' | t" [class.compact]="compact()">
      @for (l of langs; track l.code) {
        <button type="button" [class.on]="l.code === current" [attr.aria-pressed]="l.code === current"
                [attr.lang]="l.code" [title]="l.label" (click)="choose(l.code)">
          {{ compact() ? l.short : l.label }}
        </button>
      }
    </div>
  `,
  styles: `
    .lang { display: inline-flex; gap: 2px; padding: 3px; border-radius: 18px; background: var(--soft); max-width: 100%; }
    button { border: 0; background: transparent; padding: 5px 11px; border-radius: 15px; font-size: 12.5px; color: var(--ink2); white-space: nowrap; }
    button.on { background: var(--bg); color: var(--ink); font-weight: 500; box-shadow: 0 1px 3px rgba(22, 26, 51, .12); }
    .compact button { padding: 4px 8px; font-size: 11.5px; }
  `,
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class LangSwitch {
  readonly compact = input(false);
  protected readonly langs = LANGS;
  protected readonly current = LANG;

  protected choose(lang: Lang): void {
    if (lang !== this.current) setLang(lang);
  }
}
