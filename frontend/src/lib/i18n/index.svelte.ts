/**
 * Translations: English and Khmer, with no library.
 *
 * Text lives in flat dictionaries, one file per area (src/lib/i18n/en/*.ts and
 * src/lib/i18n/km/*.ts), merged at build time. A page asks for text by key:
 *
 *     {t('projects.title')}                    {t('home.greeting', { name })}
 *     {tn('projects.count', total)}            // projects.count_one / projects.count_other
 *
 * `t` reads the reactive `i18n.locale`, so every piece of text on screen updates the
 * moment the language is switched. A key missing from Khmer falls back to English, and a
 * key missing from both shows the key itself, so a gap is visible rather than blank.
 * `npm run check:i18n` lists keys that exist in one language and not the other.
 */

export type Locale = 'en' | 'km';
type Dictionary = Record<string, string>;

export const LOCALES: { value: Locale; label: string; name: string }[] = [
  { value: 'en', label: 'EN', name: 'English' },
  { value: 'km', label: 'ខ្មែរ', name: 'ខ្មែរ' }
];

function merge(files: Record<string, { default: Dictionary }>): Dictionary {
  return Object.assign({}, ...Object.values(files).map((f) => f.default));
}

const dictionaries: Record<Locale, Dictionary> = {
  en: merge(import.meta.glob<{ default: Dictionary }>('./en/*.ts', { eager: true })),
  km: merge(import.meta.glob<{ default: Dictionary }>('./km/*.ts', { eager: true }))
};

const KEY = 'sorya.locale';

export const i18n = $state<{ locale: Locale }>({ locale: 'en' });

/** The saved choice, else the browser's language (Khmer browsers get Khmer), else English. */
export function initLocale(): void {
  let chosen: Locale | null = null;
  try {
    const saved = localStorage.getItem(KEY);
    if (saved === 'en' || saved === 'km') chosen = saved;
  } catch {
    // no storage: fall through
  }
  if (!chosen) chosen = navigator.language?.toLowerCase().startsWith('km') ? 'km' : 'en';
  apply(chosen);
}

export function setLocale(locale: Locale): void {
  apply(locale);
  try {
    localStorage.setItem(KEY, locale);
  } catch {
    // The choice just lasts until the page closes.
  }
}

function apply(locale: Locale): void {
  i18n.locale = locale;
  if (typeof document !== 'undefined') document.documentElement.lang = locale;
}

function fill(text: string, params?: Record<string, string | number>): string {
  return params ? text.replace(/\{(\w+)\}/g, (_, k) => String(params[k] ?? `{${k}}`)) : text;
}

/** Text for `key` in the current language. */
export function t(key: string, params?: Record<string, string | number>): string {
  const text = dictionaries[i18n.locale][key] ?? dictionaries.en[key] ?? key;
  return fill(text, params);
}

/** Text with a count: `key_one` for exactly one in English, `key_other` otherwise
 * (Khmer has no plural forms, so it only needs `key_other`). `{n}` is filled in. */
export function tn(key: string, n: number, params: Record<string, string | number> = {}): string {
  const form = i18n.locale === 'en' && n === 1 ? 'one' : 'other';
  return t(`${key}_${form}`, { n, ...params });
}

/** Whether `key` exists in both languages (used by the check script and tests). */
export const dictionariesForCheck = dictionaries;
