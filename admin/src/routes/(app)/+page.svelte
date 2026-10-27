<script lang="ts">
  /** The headline numbers across all events: traffic, errors, AI, renders, browser vitals. */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import BarList from '$lib/components/telemetry/BarList.svelte';
  import DataTable from '$lib/components/telemetry/DataTable.svelte';
  import StatTile from '$lib/components/telemetry/StatTile.svelte';
  import TimeChart, { type ChartPoint } from '$lib/components/telemetry/TimeChart.svelte';
  import { compact, duration, percent, tone as healthTone, usd } from '$lib/components/telemetry/format';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import { RANGES, admin, fromParams, toParams, type Overview } from '$lib/telemetry/admin';
  import { users, type Stats } from '$lib/api/users';
  import { auth } from '$lib/stores/auth.svelte';

  const filters = $derived(fromParams(page.url.searchParams));
  let data = $state<Overview | null>(null);
  let people = $state<Stats | null>(null);
  $effect(() => {
    users.stats().then((s) => (people = s)).catch(() => {});
  });
  let loading = $state(false);
  let error = $state<unknown>(null);

  let generation = 0;
  async function load() {
    const mine = ++generation;
    loading = true;
    try {
      const result = await admin.overview(filters);
      if (mine === generation) (data = result), (error = null);
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
    void goto(`/${query ? `?${query}` : ''}`, { replaceState: true, noScroll: true });
  };

  const stale = $derived(loading && data !== null);
  const points = $derived<ChartPoint[]>(
    (data?.histogram.buckets ?? []).map((b) => ({ t: b.t, frontend: b.frontend, backend: b.backend, worker: b.worker, errors: b.errors }))
  );
  const apiRate = $derived(data && data.api.requests ? data.api.errors / data.api.requests : null);
  const renderRate = $derived(data && data.renders.jobs ? (data.renders.jobs - data.renders.failed) / data.renders.jobs : null);
  const rateState = (rate: number | null, good: number, poor: number) => {
    const t = healthTone(rate, good, poor);
    return t === null
      ? undefined
      : t === 'good'
        ? { tone: 'good' as const, label: 'Healthy' }
        : t === 'warning'
          ? { tone: 'warning' as const, label: 'Watch' }
          : { tone: 'critical' as const, label: 'Failing' };
  };
  // Google's published Core Web Vitals thresholds: [good, poor], ms except CLS.
  const VITAL: Record<string, [number, number, string]> = {
    LCP: [2500, 4000, 'Largest paint'],
    FCP: [1800, 3000, 'First paint'],
    INP: [200, 500, 'Interaction delay'],
    CLS: [0.1, 0.25, 'Layout shift'],
    TTFB: [800, 1800, 'Server response']
  };
  type Model = NonNullable<typeof data>['llm']['by_model'][number];
  const modelColumns = [
    { key: 'call', label: 'Call', value: (r: Model) => r.call },
    { key: 'provider', label: 'Provider', value: (r: Model) => r.provider ?? '–' },
    { key: 'model', label: 'Model', value: (r: Model) => r.model ?? '–', wide: true },
    { key: 'calls', label: 'Calls', value: (r: Model) => r.calls, numeric: true },
    { key: 'failures', label: 'Failed', value: (r: Model) => r.failures, numeric: true },
    { key: 'tokens', label: 'Tokens', value: (r: Model) => r.tokens, text: (r: Model) => compact(r.tokens), numeric: true },
    { key: 'avg', label: 'Avg time', value: (r: Model) => r.avg_ms, text: (r: Model) => duration(r.avg_ms), numeric: true },
    { key: 'cost', label: 'Cost', value: (r: Model) => r.cost_usd, text: (r: Model) => usd(r.cost_usd), numeric: true }
  ];
</script>

<svelte:head><title>Overview · Sorya Admin</title></svelte:head>

<header>
  <h1 class="text-2xl font-bold tracking-tight text-slate-50">Overview</h1>
  <p class="text-sm text-slate-400">The headline numbers across the product.</p>
</header>

<div class="flex flex-wrap items-center gap-3">
  <div class="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5" role="radiogroup" aria-label="Time range">
    {#each RANGES as r (r.value)}
      <button type="button" role="radio" aria-checked={filters.range === r.value} title={r.hint} class="rounded-md px-2.5 py-1 text-xs font-medium transition {filters.range === r.value ? 'bg-slate-700 text-slate-50' : 'text-slate-400 hover:text-slate-200'}" onclick={() => setRange(r.value)}>{r.label}</button>
    {/each}
  </div>
</div>

<ErrorBanner {error} />

{#if people}
  <section class="grid grid-cols-2 gap-3 sm:grid-cols-4">
    <StatTile label="Accounts" value={compact(people.users)} sub={`${people.active} active`} />
    <StatTile label="New this week" value={compact(people.new_7d)} />
    <StatTile label="Administrators" value={compact(people.admins)} />
    <StatTile label="Projects created" value={compact(people.projects)} />
  </section>
{/if}

{#if data}
  <section class="grid gap-3 lg:grid-cols-[minmax(0,1.1fr)_minmax(0,2.2fr)]">
    <StatTile hero label="Events recorded" value={compact(data.totals.events)} sub={`${compact(data.by_source.frontend ?? 0)} browser · ${compact(data.by_source.backend ?? 0)} API · ${compact(data.by_source.worker ?? 0)} worker`} {stale} />
    <div class="grid grid-cols-2 gap-3 sm:grid-cols-4">
      <StatTile label="People" value={compact(data.totals.users)} sub={`${compact(data.totals.sessions)} sessions`} {stale} />
      <StatTile label="Errors" value={compact(data.totals.errors)} sub={`${compact(data.totals.warnings)} warnings`} state={data.totals.errors ? { tone: 'warning', label: `${data.totals.errors} errors` } : { tone: 'good', label: 'No errors' }} {stale} />
      <StatTile label="API requests" value={compact(data.api.requests)} sub={data.api.requests ? `p50 ${duration(data.api.p50_ms)} · p95 ${duration(data.api.p95_ms)}` : 'None yet'} {stale} />
      <StatTile label="API error rate" value={percent(apiRate)} sub="Failed requests (4xx + 5xx)" state={rateState(apiRate, 0.05, 0.2)} {stale} />
      <StatTile label="AI calls" value={compact(data.llm.calls)} sub={data.llm.failures ? `${data.llm.failures} failed` : 'None failed'} {stale} />
      <StatTile label="AI tokens" value={compact(data.llm.tokens)} sub={data.llm.cost_usd === null ? 'No prices set' : `${usd(data.llm.cost_usd)} estimated`} {stale} />
      <StatTile label="Renders" value={compact(data.renders.jobs)} sub={data.renders.jobs ? `avg ${duration(data.renders.avg_ms)} · p95 ${duration(data.renders.p95_ms)}` : 'None yet'} {stale} />
      <StatTile label="Render success" value={renderRate === null ? '–' : percent(renderRate, 0)} state={renderRate === null ? undefined : rateState(1 - renderRate, 0.05, 0.2)} {stale} />
    </div>
  </section>

  <TimeChart
    title="Events over time"
    subtitle="By source, with errors from all sources as a line"
    {points}
    series={[
      { key: 'frontend', label: 'Browser', color: 'var(--series-1)', type: 'bar' },
      { key: 'backend', label: 'API', color: 'var(--series-2)', type: 'bar' },
      { key: 'worker', label: 'Worker', color: 'var(--series-3)', type: 'bar' },
      { key: 'errors', label: 'Errors', color: 'var(--status-critical)', type: 'line' }
    ]}
    {stale}
  />

  <div class="grid gap-3 lg:grid-cols-2">
    <BarList title="Most frequent events" rows={data.top_events.map((t) => ({ label: t.name, value: t.count }))} {stale} />
    <section class="min-w-0 rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4">
      <h3 class="text-sm font-semibold text-[var(--viz-ink)]">Browser performance</h3>
      <p class="mt-0.5 mb-3 text-xs text-[var(--viz-ink-3)]">75th percentile across page loads</p>
      {#if !data.web_vitals.length}
        <p class="py-6 text-center text-xs text-[var(--viz-ink-3)]">No web vitals in this range.</p>
      {:else}
        <ul class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {#each data.web_vitals as v (v.metric)}
            {@const spec = VITAL[v.metric]}
            <li>
              <StatTile
                label={spec?.[2] ?? v.metric}
                value={v.p75 === null ? '–' : v.metric === 'CLS' ? v.p75.toFixed(3) : duration(v.p75)}
                sub={`${v.metric} · ${v.samples} samples`}
                state={spec && v.p75 !== null ? (healthTone(v.p75, spec[0], spec[1]) === 'good' ? { tone: 'good', label: 'Good' } : healthTone(v.p75, spec[0], spec[1]) === 'warning' ? { tone: 'warning', label: 'Needs work' } : { tone: 'critical', label: 'Poor' }) : undefined}
                {stale}
              />
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </div>

  <DataTable title="AI calls by model" subtitle="Tokens and cost are the provider's own when reported" rows={data.llm.by_model} columns={modelColumns} id={(r) => `${r.call}|${r.provider}|${r.model}`} initialSort={{ key: 'calls', dir: 'desc' }} {stale} emptyText="No AI calls in this range." />
{:else if !error}
  <p class="py-16 text-center text-sm text-slate-400">Loading…</p>
{/if}
