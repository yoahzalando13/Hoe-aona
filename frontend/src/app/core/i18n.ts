/**
 * Traduction de l'interface : malgache, français, anglais.
 *
 * Le texte français sert de clé (et de repli si une traduction manque) : `{{ 'Fil média' | t }}`,
 * `t('Analyse supprimée')`. Les paramètres s'écrivent `{nom}` : `t('{n} analyses', { n: 3 })`.
 * Changer de langue recharge la page : dates, constantes et contenus suivent alors la nouvelle langue.
 */
import { Pipe, PipeTransform } from '@angular/core';
import { EN } from '../i18n/en';
import { MG } from '../i18n/mg';

export type Lang = 'mg' | 'fr' | 'en';

export const LANGS: { code: Lang; label: string; short: string }[] = [
  { code: 'mg', label: 'Malagasy', short: 'MG' },
  { code: 'fr', label: 'Français', short: 'FR' },
  { code: 'en', label: 'English', short: 'EN' },
];

const STORAGE_KEY = 'hoe-aona.lang';
const DICTS: Record<Lang, Record<string, string> | null> = { fr: null, en: EN, mg: MG };

function detect(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'mg' || saved === 'fr' || saved === 'en') return saved;
  } catch { /* stockage indisponible */ }
  const nav = (typeof navigator !== 'undefined' ? navigator.language : 'fr').slice(0, 2).toLowerCase();
  return nav === 'mg' || nav === 'en' ? nav : 'fr';
}

/** Langue de la session, fixée au chargement de la page. */
export const LANG: Lang = detect();

/** Locale Angular / Intl correspondante (dates, nombres). */
export const LOCALE: string = LANG;

export function t(fr: string, params?: Record<string, string | number | null | undefined>): string {
  const text = DICTS[LANG]?.[fr] ?? fr;
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (m, k: string) => (params[k] ?? m).toString());
}

/** Pluriel simple : `plural(n, '{n} analyse', '{n} analyses')`. */
export function plural(n: number, one: string, many: string): string {
  return t(n > 1 ? many : one, { n });
}

/** Applique la langue enregistrée dans le compte, si elle diffère de celle de la page (rechargement). */
export function applyLang(lang: string | null | undefined): void {
  if ((lang === 'mg' || lang === 'fr' || lang === 'en') && lang !== LANG) setLang(lang);
}

export function setLang(lang: Lang): void {
  try { localStorage.setItem(STORAGE_KEY, lang); } catch { /* stockage indisponible */ }
  location.reload();
}

@Pipe({ name: 't' })
export class TPipe implements PipeTransform {
  transform(fr: string | null | undefined, params?: Record<string, string | number | null | undefined>): string {
    return fr ? t(fr, params) : "";
  }
}

/** `{{ total() | plural: '{n} analyse' : '{n} analyses' }}` */
@Pipe({ name: 'plural' })
export class PluralPipe implements PipeTransform {
  transform(n: number | null | undefined, one: string, many: string): string {
    return plural(n ?? 0, one, many);
  }
}
