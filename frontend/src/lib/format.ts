/** Small display helpers shared by the app's pages. */

import { t } from '$lib/i18n/index.svelte';

/** "just now", "2h ago", "3d ago", or the date once it is older than a week. */
export function ago(iso: string): string {
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return t('time.justNow');
  if (s < 3600) return t('time.minAgo', { n: Math.floor(s / 60) });
  if (s < 86400) return t('time.hourAgo', { n: Math.floor(s / 3600) });
  if (s < 7 * 86400) return t('time.dayAgo', { n: Math.floor(s / 86400) });
  return new Date(iso).toLocaleDateString();
}

/** 83 -> "1:23". */
export function mmss(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, '0')}`;
}

/** 1536 -> "1.5 KB", 3.2e9 -> "3.0 GB". */
export function bytes(n: number): string {
  if (n < 1024) return `${n} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let value = n / 1024;
  let i = 0;
  while (value >= 1024 && i < units.length - 1) {
    value /= 1024;
    i += 1;
  }
  return `${value >= 100 || i === 0 ? Math.round(value) : value.toFixed(1)} ${units[i]}`;
}

/** The pretty length of a template or a video: "30s", "1 min", "1.5 min" (Khmer units in Khmer). */
export function length(seconds: number): string {
  return seconds < 60
    ? t('time.seconds', { n: seconds })
    : t('time.minutes', { n: Math.round((seconds / 60) * 10) / 10 });
}
