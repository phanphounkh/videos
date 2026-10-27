/** Per-browser defaults for new videos, set on the Settings page. */

export interface Preferences {
  language: 'en' | 'km';
  purpose: string;
}

const KEY = 'sorya.preferences';
const DEFAULTS: Preferences = { language: 'en', purpose: 'story' };

export function loadPreferences(): Preferences {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) ?? '{}') as Partial<Preferences>;
    return {
      language: raw.language === 'km' ? 'km' : 'en',
      purpose: typeof raw.purpose === 'string' && raw.purpose ? raw.purpose : DEFAULTS.purpose
    };
  } catch {
    return { ...DEFAULTS };
  }
}

export function savePreferences(next: Preferences): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Without storage the choice just lasts until the page closes.
  }
}
