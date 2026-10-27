<script lang="ts">
  /** One row per browser session, with how much the server did for it. */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { ago, compact } from '$lib/components/telemetry/format';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import DataTable from '$lib/components/telemetry/DataTable.svelte';
  import { RANGES, admin, fromParams, shortId, toParams, who, type SessionRow } from '$lib/telemetry/admin';
  import { auth } from '$lib/stores/auth.svelte';

  const filters = $derived(fromParams(page.url.searchParams));
  let rows = $state<SessionRow[]>([]);
  let loading = $state(false);
  let error = $state<unknown>(null);

  let generation = 0;
  async function load() {
    const mine = ++generation;
    loading = true;
    try {
      const result = await admin.sessions(filters);
      if (mine === generation) {
        rows = result.sessions;
        error = null;
      }
    } catch (e) {
      if (mine === generation) error = e;
    } finally {
      if (mine === generation) loading = false;
    }
  }
  $effect(() => {
    void page.url.search;
    if (auth.user?.is_admin) void load();
  });

  const setRange = (range: (typeof RANGES)[number]['value']) => {
    const query = toParams({ ...filters, range }).toString();
    void goto(`/sessions${query ? `?${query}` : ''}`, { replaceState: true, noScroll: true });
  };

  const span = (s: number) => (s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${(s / 3600).toFixed(1)}h`);
  const columns = [
    { key: 'last', label: 'Last seen', value: (r: SessionRow) => r.last_seen, text: (r: SessionRow) => ago(r.last_seen) },
    { key: 'who', label: 'Who', value: (r: SessionRow) => who(r), wide: true },
    { key: 'dur', label: 'Length', value: (r: SessionRow) => r.duration_s, text: (r: SessionRow) => span(r.duration_s), numeric: true },
    { key: 'pages', label: 'Pages', value: (r: SessionRow) => r.pages, numeric: true },
    { key: 'events', label: 'Events', value: (r: SessionRow) => r.events, text: (r: SessionRow) => compact(r.events), numeric: true },
    { key: 'server', label: 'Server events', value: (r: SessionRow) => r.backend_events, text: (r: SessionRow) => compact(r.backend_events), numeric: true },
    { key: 'errors', label: 'Errors', value: (r: SessionRow) => r.errors, numeric: true },
    { key: 'client', label: 'Client', value: (r: SessionRow) => [r.platform, r.browser].filter(Boolean).join(' · ') || '–' },
    { key: 'id', label: 'Session', value: (r: SessionRow) => shortId(r.session_id) }
  ];
</script>

<svelte:head><title>Sessions · Sorya Admin</title></svelte:head>

<header>
  <h1 class="text-2xl font-bold tracking-tight text-slate-50">Sessions</h1>
  <p class="text-sm text-slate-400">One row per browser session, with the server work it caused.</p>
</header>

<div class="flex flex-wrap items-center gap-3">
  <div class="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5" role="radiogroup" aria-label="Time range">
    {#each RANGES as r (r.value)}
      <button type="button" role="radio" aria-checked={filters.range === r.value} title={r.hint} class="rounded-md px-2.5 py-1 text-xs font-medium transition {filters.range === r.value ? 'bg-slate-700 text-slate-50' : 'text-slate-400 hover:text-slate-200'}" onclick={() => setRange(r.value)}>{r.label}</button>
    {/each}
  </div>
  <span class="text-xs text-slate-400">{rows.length} sessions · open one to see everything that happened, in order</span>
</div>

<ErrorBanner {error} />

<DataTable
  title="Sessions"
  subtitle="Click a row for its timeline"
  {rows}
  {columns}
  id={(r) => r.session_id}
  initialSort={{ key: 'last', dir: 'desc' }}
  stale={loading && rows.length > 0}
  emptyText={loading ? 'Loading…' : 'No sessions in this range.'}
>
  {#snippet detail(r: SessionRow)}
    <p class="text-xs text-[var(--viz-ink-2)]">
      <a class="font-semibold text-sun-300 hover:text-sun-200" href="/sessions/{r.session_id}">Open the timeline</a>
      {#if r.user_id}
        · <a class="text-sun-300 hover:text-sun-200" href="/users/{r.user_id}">user page</a>
      {/if}
      · <a class="text-sun-300 hover:text-sun-200" href="/events?session={r.session_id}&range=90d">events</a>
    </p>
  {/snippet}
</DataTable>
