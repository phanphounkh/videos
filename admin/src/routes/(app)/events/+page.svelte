<script lang="ts">
  /**
   * The event explorer: every event, newest first, with the filters that make it usable.
   * The filters are the URL. "Live" keeps pulling whatever has arrived since the newest
   * row on screen, so you can watch the system as it happens.
   */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import EventList from '$lib/components/telemetry/EventList.svelte';
  import TimeChart, { type ChartPoint } from '$lib/components/telemetry/TimeChart.svelte';
  import { compact } from '$lib/components/telemetry/format';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import {
    RANGES,
    activeCount,
    admin,
    emptyFilters,
    exportEvents,
    fromParams,
    toParams,
    type Facets,
    type Filters,
    type Histogram,
    type TEvent
  } from '$lib/telemetry/admin';
  import { auth } from '$lib/stores/auth.svelte';

  const PAGE = 100;
  const LIVE_MS = 2_000;
  const MAX_LIVE_ROWS = 1_000;

  const filters = $derived(fromParams(page.url.searchParams));
  const isAdmin = $derived(!!auth.user?.is_admin);

  let events = $state<TEvent[]>([]);
  let next = $state<string | null>(null);
  let total = $state<number | null>(null);
  let facets = $state<Facets | null>(null);
  let histogram = $state<Histogram | null>(null);
  let loading = $state(false);
  let error = $state<unknown>(null);
  let live = $state(false);
  let latestSeq = $state(0);
  let fresh = $state(new Set<string>());
  let search = $state('');

  /** Writes the filters to the URL; the effect below reloads from it. */
  function apply(next: Filters) {
    const query = toParams(next).toString();
    void goto(`/events${query ? `?${query}` : ''}`, { replaceState: true, keepFocus: true, noScroll: true });
  }
  function toggle(key: 'source' | 'event_type' | 'name' | 'level' | 'outcome' | 'platform', value: string) {
    const list = filters[key];
    apply({ ...filters, [key]: list.includes(value) ? list.filter((v) => v !== value) : [...list, value] });
  }

  let generation = 0;
  async function load() {
    const mine = ++generation;
    loading = true;
    try {
      const f = filters;
      const [list, fac, hist] = await Promise.all([
        admin.events(f, { limit: PAGE, include_total: true }),
        admin.facets(f),
        admin.histogram(f)
      ]);
      // A slower, older answer must not overwrite a newer filter's results.
      if (mine !== generation) return;
      events = list.events;
      next = list.next_before;
      total = list.total;
      latestSeq = list.latest_seq;
      facets = fac;
      histogram = hist;
      error = null;
    } catch (e) {
      if (mine === generation) error = e;
    } finally {
      if (mine === generation) loading = false;
    }
  }

  async function more() {
    if (!next || loading) return;
    loading = true;
    try {
      const list = await admin.events(filters, { limit: PAGE, before: next });
      events = [...events, ...list.events];
      next = list.next_before;
    } catch (e) {
      error = e;
    } finally {
      loading = false;
    }
  }

  // Reload whenever the filters (the URL) change, once we know this is an admin.
  $effect(() => {
    void page.url.search;
    if (isAdmin) void load();
  });
  $effect(() => {
    search = filters.q;
  });

  // Live tail: only what arrived after the newest row we hold.
  $effect(() => {
    if (!live || !isAdmin) return;
    let stop = false;
    const tick = async () => {
      try {
        const result = await admin.events(filters, { limit: 200, after_seq: latestSeq });
        if (stop || !result.events.length) {
          if (!stop) latestSeq = Math.max(latestSeq, result.latest_seq);
          return;
        }
        latestSeq = Math.max(latestSeq, ...result.events.map((e) => e.seq));
        fresh = new Set(result.events.map((e) => e.id));
        events = [...result.events, ...events].slice(0, MAX_LIVE_ROWS);
        if (total !== null) total += result.events.length;
      } catch {
        // A missed tick is fine; the next one catches up from the same sequence.
      }
    };
    const timer = setInterval(() => void tick(), LIVE_MS);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  });

  const points = $derived<ChartPoint[]>(
    (histogram?.buckets ?? []).map((b) => ({ t: b.t, frontend: b.frontend, backend: b.backend, worker: b.worker, errors: b.errors }))
  );
  const spanSeconds = $derived(
    histogram && histogram.buckets.length ? histogram.bucket_seconds * histogram.buckets.length : 0
  );

  const FACETS = [
    { key: 'source', label: 'Source' },
    { key: 'event_type', label: 'Type' },
    { key: 'level', label: 'Level' },
    { key: 'outcome', label: 'Outcome' },
    { key: 'platform', label: 'Platform' },
    { key: 'name', label: 'Event name' }
  ] as const;

  const pills = $derived(
    [
      ...(['source', 'event_type', 'name', 'level', 'outcome', 'platform'] as const).flatMap((k) =>
        filters[k].map((v) => ({ label: `${k.replace('_', ' ')}: ${v}`, clear: () => toggle(k, v) }))
      ),
      ...filters.hide.map((v) => ({ label: `hiding ${v}`, clear: () => apply({ ...filters, hide: filters.hide.filter((h) => h !== v) }) })),
      ...(filters.user ? [{ label: `user ${filters.user.slice(0, 8)}`, clear: () => apply({ ...filters, user: '' }) }] : []),
      ...(filters.session ? [{ label: `session ${filters.session.slice(0, 8)}`, clear: () => apply({ ...filters, session: '' }) }] : []),
      ...(filters.request_id ? [{ label: `request ${filters.request_id.slice(0, 8)}`, clear: () => apply({ ...filters, request_id: '' }) }] : []),
      ...(filters.path ? [{ label: `path ${filters.path}`, clear: () => apply({ ...filters, path: '' }) }] : []),
      ...(filters.anonymous ? [{ label: 'signed out only', clear: () => apply({ ...filters, anonymous: false }) }] : [])
    ]
  );

  async function download(format: 'json' | 'csv') {
    try {
      await exportEvents(filters, format);
    } catch (e) {
      error = e;
    }
  }
</script>

<svelte:head><title>Events · Sorya Admin</title></svelte:head>

<header>
  <h1 class="text-2xl font-bold tracking-tight text-slate-50">Events</h1>
  <p class="text-sm text-slate-400">Every event from the browser, the API and the workers.</p>
</header>

<div class="flex flex-wrap items-center gap-2">
  <div class="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5" role="radiogroup" aria-label="Time range">
    {#each RANGES as r (r.value)}
      <button
        type="button"
        role="radio"
        aria-checked={filters.range === r.value}
        title={r.hint}
        class="rounded-md px-2.5 py-1 text-xs font-medium transition {filters.range === r.value ? 'bg-slate-700 text-slate-50' : 'text-slate-400 hover:text-slate-200'}"
        onclick={() => apply({ ...filters, range: r.value })}>{r.label}</button
      >
    {/each}
  </div>

  <form
    class="relative min-w-52 flex-1 sm:max-w-md"
    onsubmit={(e) => {
      e.preventDefault();
      apply({ ...filters, q: search.trim() });
    }}
  >
    <input
      type="search"
      bind:value={search}
      placeholder="Search names, paths, messages, properties…"
      aria-label="Search events"
      data-private
      class="h-8 w-full rounded-lg border border-slate-700 bg-slate-900 pr-3 pl-3 text-xs text-slate-100 placeholder:text-slate-500 focus:border-sun-400 focus:outline-none"
    />
  </form>

  <button
    type="button"
    aria-pressed={live}
    class="inline-flex h-8 items-center gap-1.5 rounded-lg border px-3 text-xs font-semibold transition {live ? 'border-sun-400 bg-sun-400/15 text-sun-200' : 'border-slate-700 bg-slate-800 text-slate-100 hover:bg-slate-700'}"
    onclick={() => (live = !live)}
  >
    <span class="h-2 w-2 rounded-full {live ? 'animate-pulse bg-sun-400' : 'bg-slate-500'}"></span>
    {live ? 'Live' : 'Go live'}
  </button>
  <button type="button" class="inline-flex h-8 items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 text-xs font-semibold text-slate-100 transition hover:bg-slate-700 disabled:opacity-50" disabled={loading} onclick={() => void load()}>
    <span class={loading ? 'animate-spin' : ''}><Icon name="redo" size={13} /></span> Refresh
  </button>
  <div class="ml-auto flex items-center gap-1 text-xs text-slate-400">
    <Icon name="download" size={13} /> Export
    <button type="button" class="rounded px-1.5 py-0.5 font-medium text-slate-200 hover:bg-slate-800" onclick={() => download('csv')}>CSV</button>
    <button type="button" class="rounded px-1.5 py-0.5 font-medium text-slate-200 hover:bg-slate-800" onclick={() => download('json')}>JSON</button>
  </div>
</div>

{#if pills.length}
  <div class="flex flex-wrap items-center gap-1.5">
    {#each pills as pill (pill.label)}
      <button type="button" class="inline-flex items-center gap-1 rounded-full border border-slate-700 bg-slate-800 py-0.5 pr-1.5 pl-2.5 text-xs text-slate-200 hover:bg-slate-700" onclick={pill.clear} aria-label={`Remove filter ${pill.label}`}>
        {pill.label} <Icon name="x" size={11} />
      </button>
    {/each}
    {#if filters.q}
      <span class="text-xs text-slate-400">matching “{filters.q}”</span>
    {/if}
    <button type="button" class="text-xs text-sun-300 hover:text-sun-200" onclick={() => apply({ ...emptyFilters(), range: filters.range })}>Clear all</button>
  </div>
{/if}

<ErrorBanner {error} />

<div class="grid gap-4 lg:grid-cols-[15rem_minmax(0,1fr)]">
  <!-- facets: counts for every alternative, each ignoring its own filter -->
  <aside class="min-w-0 space-y-4 text-xs lg:max-h-[calc(100dvh-14rem)] lg:overflow-y-auto lg:pr-1" aria-label="Filters">
    {#if facets}
      {#each FACETS as facet (facet.key)}
        {#if facets[facet.key].length}
          <section>
            <h3 class="mb-1.5 font-semibold text-[var(--viz-ink-2)]">{facet.label}</h3>
            <ul class="space-y-0.5">
              {#each facets[facet.key] as item (item.value)}
                <li>
                  <label class="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 hover:bg-slate-800/50">
                    <input type="checkbox" class="shrink-0" checked={filters[facet.key].includes(item.value)} onchange={() => toggle(facet.key, item.value)} />
                    <span class="min-w-0 flex-1 truncate text-[var(--viz-ink)]" title={item.value}>{item.value}</span>
                    <span class="text-[var(--viz-ink-3)] tabular-nums">{compact(item.count)}</span>
                  </label>
                </li>
              {/each}
            </ul>
          </section>
        {/if}
      {/each}
      <section>
        <h3 class="mb-1.5 font-semibold text-[var(--viz-ink-2)]">Signed in</h3>
        <label class="flex cursor-pointer items-center gap-2 rounded px-1.5 py-1 hover:bg-slate-800/50">
          <input type="checkbox" checked={filters.anonymous} onchange={() => apply({ ...filters, anonymous: !filters.anonymous })} />
          <span class="flex-1 text-[var(--viz-ink)]">Signed out only</span>
          <span class="text-[var(--viz-ink-3)] tabular-nums">{compact(facets.anonymous)}</span>
        </label>
      </section>
    {:else if !error}
      <p class="text-[var(--viz-ink-3)]">Loading filters…</p>
    {/if}
  </aside>

  <div class="min-w-0 space-y-4">
    <TimeChart
      title="Events over time"
      subtitle={total === null ? '' : `${compact(total)} matching`}
      points={points}
      series={[
        { key: 'frontend', label: 'Browser', color: 'var(--series-1)', type: 'bar' },
        { key: 'backend', label: 'API', color: 'var(--series-2)', type: 'bar' },
        { key: 'worker', label: 'Worker', color: 'var(--series-3)', type: 'bar' },
        { key: 'errors', label: 'Errors (all sources)', color: 'var(--status-critical)', type: 'line' }
      ]}
      height={150}
      stale={loading && histogram !== null}
      emptyText="No events in this range."
    />

    <section class="rounded-xl border border-slate-800 bg-[var(--viz-surface)]">
      <header class="flex items-center justify-between gap-3 border-b border-[var(--viz-grid)] px-4 py-2.5">
        <h2 class="text-sm font-semibold text-[var(--viz-ink)]">
          Events
          <span class="font-normal text-[var(--viz-ink-3)]">
            {#if total !== null}· showing {compact(events.length)} of {compact(total)}{/if}
            {#if activeCount(filters)}· filtered{/if}
          </span>
        </h2>
        {#if live}<span class="text-xs text-sun-300">Streaming new events…</span>{/if}
      </header>
      <div class="transition-opacity {loading && events.length ? 'opacity-60' : ''}">
        <EventList {events} {fresh} emptyText={loading ? 'Loading…' : 'No events match these filters.'} />
      </div>
      {#if next}
        <div class="border-t border-[var(--viz-grid)] p-3 text-center">
          <button type="button" class="rounded-lg border border-slate-700 bg-slate-800 px-4 py-1.5 text-xs font-semibold text-slate-100 hover:bg-slate-700 disabled:opacity-50" disabled={loading} onclick={() => void more()}>Load older events</button>
        </div>
      {/if}
    </section>
  </div>
</div>
