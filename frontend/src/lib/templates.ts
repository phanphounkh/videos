/** Filtering the template gallery: by category, kind of video, shape or length. The same
 * filter is a URL (`/templates?purpose=explainer`), so a category card on Home is a link. */

import type { TemplateItem } from '$lib/types/api';

export type TemplateFilter = {
  category?: string;
  purpose?: string;
  aspect?: string;
  /** Only videos of at most this many seconds. */
  maxSeconds?: number;
};

export type CategoryCard = { id: string; filter: TemplateFilter; tint: string };

/** The "Browse template categories" cards. Names come from `home.cat.<id>`. */
export const CATEGORY_CARDS: CategoryCard[] = [
  { id: 'social', filter: { category: 'social' }, tint: 'from-pink-500/25 to-rose-500/10' },
  { id: 'business', filter: { category: 'business' }, tint: 'from-sky-500/25 to-blue-500/10' },
  { id: 'education', filter: { category: 'education' }, tint: 'from-emerald-500/25 to-teal-500/10' },
  { id: 'story', filter: { category: 'story' }, tint: 'from-amber-500/25 to-orange-500/10' },
  { id: 'product_demo', filter: { purpose: 'product_demo' }, tint: 'from-violet-500/25 to-purple-500/10' },
  { id: 'explainer', filter: { purpose: 'explainer' }, tint: 'from-cyan-500/25 to-sky-500/10' },
  { id: 'creator', filter: { purpose: 'creator' }, tint: 'from-fuchsia-500/25 to-pink-500/10' },
  { id: 'landscape', filter: { aspect: '16:9' }, tint: 'from-indigo-500/25 to-violet-500/10' },
  { id: 'portrait', filter: { aspect: '9:16' }, tint: 'from-orange-500/25 to-red-500/10' },
  { id: 'short', filter: { maxSeconds: 30 }, tint: 'from-lime-500/20 to-emerald-500/10' }
];

export function matches(t: TemplateItem, f: TemplateFilter): boolean {
  return (
    (!f.category || t.category === f.category) &&
    (!f.purpose || t.purpose === f.purpose) &&
    (!f.aspect || t.aspect_ratio === f.aspect) &&
    (!f.maxSeconds || t.duration <= f.maxSeconds)
  );
}

export function toQuery(f: TemplateFilter): string {
  const p = new URLSearchParams();
  if (f.category) p.set('category', f.category);
  if (f.purpose) p.set('purpose', f.purpose);
  if (f.aspect) p.set('aspect', f.aspect);
  if (f.maxSeconds) p.set('max', String(f.maxSeconds));
  const q = p.toString();
  return q ? `?${q}` : '';
}

export function fromParams(p: URLSearchParams): TemplateFilter {
  const max = Number(p.get('max'));
  return {
    category: p.get('category') ?? undefined,
    purpose: p.get('purpose') ?? undefined,
    aspect: p.get('aspect') ?? undefined,
    maxSeconds: Number.isFinite(max) && max > 0 ? max : undefined
  };
}

/** The id of the category card whose filter equals `f` (to name the active filter). */
export function cardFor(f: TemplateFilter): CategoryCard | undefined {
  return CATEGORY_CARDS.find((c) => toQuery(c.filter) === toQuery(f));
}
