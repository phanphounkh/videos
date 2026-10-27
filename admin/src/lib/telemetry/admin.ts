/**
 * The admin panel's side of telemetry: types, the filter model, and the calls to the
 * telemetry service (through /api/telemetry, see src/hooks.server.ts).
 *
 * The filters live in the URL, so a view can be bookmarked or shared, the back button
 * works, and a click on a user, session or request id elsewhere in the panel is just a
 * link to the explorer with that filter set.
 */

import { apiFetch, getToken } from '$lib/api/client';

export type Range = '15m' | '1h' | '6h' | '24h' | '7d' | '30d' | '90d';
export const RANGES: { value: Range; label: string; hint: string }[] = [
  { value: '15m', label: '15 m', hint: 'Last 15 minutes' },
  { value: '1h', label: '1 h', hint: 'Last hour' },
  { value: '6h', label: '6 h', hint: 'Last 6 hours' },
  { value: '24h', label: '24 h', hint: 'Last 24 hours' },
  { value: '7d', label: '7 d', hint: 'Last 7 days' },
  { value: '30d', label: '30 d', hint: 'Last 30 days' },
  { value: '90d', label: '90 d', hint: 'Last 90 days' }
];

export type Level = 'debug' | 'info' | 'warning' | 'error';

export interface TEvent {
  id: string;
  seq: number;
  created_at: string;
  event_type: 'llm_usage' | 'product' | 'log';
  name: string;
  source: 'backend' | 'worker' | 'frontend';
  level: Level;
  outcome: 'ok' | 'error' | null;
  user_id: string | null;
  user_email?: string | null;
  session_id: string | null;
  request_id: string | null;
  path: string | null;
  duration_ms: number | null;
  model: string | null;
  provider: string | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  finish_reason: string | null;
  cost_usd: number | null;
  properties: Record<string, unknown>;
  platform: string | null;
  os: string | null;
  browser: string | null;
}

export interface Filters {
  range: Range;
  source: string[];
  event_type: string[];
  name: string[];
  level: string[];
  outcome: string[];
  platform: string[];
  hide: string[];
  user: string;
  anonymous: boolean;
  session: string;
  request_id: string;
  path: string;
  q: string;
}

export const emptyFilters = (): Filters => ({
  range: '24h',
  source: [],
  event_type: [],
  name: [],
  level: [],
  outcome: [],
  platform: [],
  hide: [],
  user: '',
  anonymous: false,
  session: '',
  request_id: '',
  path: '',
  q: ''
});

const LISTS = ['source', 'event_type', 'name', 'level', 'outcome', 'platform', 'hide'] as const;
const TEXTS = ['user', 'session', 'request_id', 'path', 'q'] as const;

/** Filters as a query string, leaving out everything that is at its default. */
export function toParams(
  f: Filters,
  extra: Record<string, string | number | undefined> = {}
): URLSearchParams {
  const p = new URLSearchParams();
  if (f.range !== '24h') p.set('range', f.range);
  for (const key of LISTS) for (const value of f[key]) p.append(key, value);
  for (const key of TEXTS) if (f[key]) p.set(key, f[key]);
  if (f.anonymous) p.set('anonymous', 'true');
  for (const [key, value] of Object.entries(extra))
    if (value !== undefined) p.set(key, String(value));
  return p;
}

export function fromParams(p: URLSearchParams): Filters {
  const f = emptyFilters();
  const range = p.get('range') as Range | null;
  if (range && RANGES.some((r) => r.value === range)) f.range = range;
  for (const key of LISTS) f[key] = p.getAll(key);
  for (const key of TEXTS) f[key] = p.get(key) ?? '';
  f.anonymous = p.get('anonymous') === 'true';
  return f;
}

export const activeCount = (f: Filters): number =>
  LISTS.reduce((n, key) => n + f[key].length, 0) +
  TEXTS.reduce((n, key) => n + (f[key] ? 1 : 0), 0) +
  (f.anonymous ? 1 : 0);

// ----------------------------------------------------------------- responses
export interface EventsPage {
  events: TEvent[];
  next_before: string | null;
  latest_seq: number;
  total: number | null;
}
export interface Facet {
  value: string;
  count: number;
}
export interface Facets {
  total: number;
  anonymous: number;
  source: Facet[];
  event_type: Facet[];
  level: Facet[];
  outcome: Facet[];
  platform: Facet[];
  name: Facet[];
}
export interface Bucket {
  t: string;
  total: number;
  frontend: number;
  backend: number;
  worker: number;
  errors: number;
}
export interface Histogram {
  bucket_seconds: number;
  buckets: Bucket[];
}
export interface SessionRow {
  session_id: string;
  user_id: string | null;
  user_email?: string | null;
  first_seen: string;
  last_seen: string;
  duration_s: number;
  events: number;
  errors: number;
  pages: number;
  backend_events: number;
  platform: string | null;
  browser: string | null;
}
export interface SessionTimeline {
  session_id: string;
  user_id: string | null;
  user_email: string | null;
  first_seen: string;
  last_seen: string;
  events: TEvent[];
}
export interface UserRow {
  user_id: string;
  user_email?: string | null;
  events: number;
  sessions: number;
  errors: number;
  first_seen: string;
  last_seen: string;
  platform: string | null;
  browser: string | null;
}
export interface UserDetail {
  user: UserRow;
  sessions: SessionRow[];
  top_events: { name: string; count: number }[];
  errors: TEvent[];
}
export interface Overview {
  totals: {
    events: number;
    errors: number;
    warnings: number;
    users: number;
    sessions: number;
    anonymous_events: number;
  };
  by_source: Record<string, number>;
  api: {
    requests: number;
    errors: number;
    p50_ms: number | null;
    p95_ms: number | null;
  };
  llm: {
    calls: number;
    failures: number;
    tokens: number;
    cost_usd: number | null;
    avg_ms: number | null;
    by_model: {
      call: string;
      provider: string | null;
      model: string | null;
      calls: number;
      tokens: number;
      cost_usd: number | null;
      avg_ms: number | null;
      failures: number;
    }[];
  };
  renders: {
    jobs: number;
    failed: number;
    avg_ms: number | null;
    p95_ms: number | null;
  };
  web_vitals: { metric: string; samples: number; p75: number | null }[];
  top_events: { name: string; count: number }[];
  histogram: Histogram;
  since: string;
  until: string;
}
export interface LlmUsage {
  totals: {
    calls: number;
    failures: number;
    tokens: number;
    prompt_tokens: number;
    completion_tokens: number;
    cost_usd: number | null;
    avg_ms: number | null;
    p95_ms: number | null;
    users: number;
  };
  bucket_seconds: number;
  series: { t: string; calls: number; failures: number; tokens: number; cost_usd: number }[];
  by_model: {
    call: string;
    provider: string | null;
    model: string | null;
    calls: number;
    failures: number;
    tokens: number;
    cost_usd: number | null;
    avg_ms: number | null;
    p95_ms: number | null;
  }[];
  by_user: {
    user_id: string;
    user_email?: string | null;
    calls: number;
    failures: number;
    tokens: number;
    cost_usd: number | null;
  }[];
  recent_failures: TEvent[];
}

export interface Health {
  status: 'ok' | 'degraded';
  database: { ok: boolean; error?: string };
  redis: {
    ok: boolean;
    error?: string;
    stream_length?: number;
    pending?: number;
  };
  consumer: Record<string, unknown> & { state?: string };
  stored: { events?: number; last_event_at?: string | null };
}

// --------------------------------------------------------------------- calls
const get = <T>(path: string, f?: Filters, extra?: Record<string, string | number | undefined>) => {
  const query = f
    ? toParams(f, extra).toString()
    : new URLSearchParams(extra as Record<string, string>).toString();
  return apiFetch<T>(`/telemetry${path}${query ? `?${query}` : ''}`);
};

export const admin = {
  events: (
    f: Filters,
    o: {
      limit?: number;
      before?: string | null;
      after_seq?: number;
      include_total?: boolean;
    } = {}
  ) =>
    get<EventsPage>('/events', f, {
      limit: o.limit,
      before: o.before ?? undefined,
      after_seq: o.after_seq,
      include_total: o.include_total ? 'true' : undefined
    }),
  facets: (f: Filters) => get<Facets>('/events/facets', f),
  histogram: (f: Filters) => get<Histogram>('/events/histogram', f),
  event: (id: string) => get<{ event: TEvent; same_request: TEvent[] }>(`/events/${id}`),
  sessions: (f: Filters) => get<{ sessions: SessionRow[] }>('/sessions', f),
  timeline: (id: string) => get<SessionTimeline>(`/sessions/${encodeURIComponent(id)}/timeline`),
  users: (f: Filters) => get<{ users: UserRow[] }>('/users', f),
  user: (id: string, f: Filters) => get<UserDetail>(`/users/${encodeURIComponent(id)}`, f),
  overview: (f: Filters) => get<Overview>('/overview', f),
  llm: (f: Filters) => get<LlmUsage>('/llm', f),
  health: () => apiFetch<Health>('/telemetry/health/checks')
};

/** Downloads the current filter as a file. A plain link cannot carry the bearer token. */
export async function exportEvents(f: Filters, format: 'json' | 'csv'): Promise<void> {
  const token = getToken();
  const response = await fetch(`/api/telemetry/events/export?${toParams(f, { format })}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {}
  });
  if (!response.ok) throw new Error(`Export failed (${response.status})`);
  const blob = await response.blob();
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `events.${format}`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// ------------------------------------------------------------------ display
export const clock = (iso: string): string => {
  const d = new Date(iso);
  return `${d.toLocaleTimeString([], { hour12: false })}.${String(d.getMilliseconds()).padStart(3, '0')}`;
};
export const day = (iso: string): string =>
  new Date(iso).toLocaleDateString([], { month: 'short', day: 'numeric' });
export const shortId = (id: string | null | undefined): string => (id ? id.slice(0, 8) : '–');
export const who = (e: { user_email?: string | null; user_id: string | null }): string =>
  e.user_email ?? (e.user_id ? shortId(e.user_id) : 'anonymous');

/** One line saying what an event is about, from the fields that matter for its kind. */
export function summary(e: TEvent): string {
  const p = e.properties;
  const str = (k: string) =>
    typeof p[k] === 'string' || typeof p[k] === 'number' ? String(p[k]) : '';
  if (e.name === 'api_request')
    return `${str('method')} ${str('route') || e.path || ''} → ${str('status_code')}`;
  if (e.name === 'network_request')
    return `${str('method')} ${str('api_path')} → ${str('status_code')}`;
  if (e.name === 'click' || e.name === 'rage_click')
    return [str('tag'), str('label')].filter(Boolean).join(' · ');
  if (e.name === 'web_vital') return `${str('metric')} ${str('value')}`;
  if (e.event_type === 'llm_usage')
    return [e.provider, e.model, e.total_tokens ? `${e.total_tokens} tokens` : '']
      .filter(Boolean)
      .join(' · ');
  if (e.level === 'error' || e.name.endsWith('error') || e.name.endsWith('rejection'))
    return str('message') || str('error') || str('exception') || str('error_code') || e.path || '';
  return e.path ?? str('state') ?? '';
}
