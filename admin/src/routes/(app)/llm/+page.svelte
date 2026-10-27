<script lang="ts">
  /** AI usage across the product: how much, which models, who, what it costs, what failed. */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import DataTable from '$lib/components/telemetry/DataTable.svelte';
  import EventList from '$lib/components/telemetry/EventList.svelte';
  import StatTile from '$lib/components/telemetry/StatTile.svelte';
  import TimeChart, { type ChartPoint } from '$lib/components/telemetry/TimeChart.svelte';
  import { compact, duration, percent, usd } from '$lib/components/telemetry/format';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import { RANGES, admin, fromParams, toParams, type LlmUsage } from '$lib/telemetry/admin';

  const filters = $derived(fromParams(page.url.searchParams));
  let data = $state<LlmUsage | null>(null);
  let loading = $state(false);
  let error = $state<unknown>(null);

  let generation = 0;
  $effect(() => {
    void page.url.search;
    const mine = ++generation;
    loading = true;
    admin
      .llm({ ...filters, range: page.url.searchParams.get('range') ? filters.range : '7d' })
      .then((d) => mine === generation && ((data = d), (error = null)))
      .catch((e) => mine === generation && (error = e))
      .finally(() => mine === generation && (loading = false));
  });
  const range = $derived(page.url.searchParams.get('range') ? filters.range : '7d');
  const setRange = (r: (typeof RANGES)[number]['value']) => {
    const q = toParams({ ...filters, range: r }, { range: r }).toString();
    void goto(`/llm?${q}`, { replaceState: true, noScroll: true });
  };

  const stale = $derived(loading && data !== null);
  const calls = $derived<ChartPoint[]>(
    (data?.series ?? []).map((p) => ({ t: p.t, ok: p.calls - p.failures, failed: p.failures }))
  );
  const tokens = $derived<ChartPoint[]>((data?.series ?? []).map((p) => ({ t: p.t, tokens: p.tokens })));
  const cost = $derived<ChartPoint[]>((data?.series ?? []).map((p) => ({ t: p.t, cost: p.cost_usd })));
  const failRate = $derived(data && data.totals.calls ? data.totals.failures / data.totals.calls : null);

  type Model = NonNullable<typeof data>['by_model'][number];
  type Person = NonNullable<typeof data>['by_user'][number];
  const modelColumns = [
    { key: 'call', label: 'Call', value: (r: Model) => r.call },
    { key: 'provider', label: 'Provider', value: (r: Model) => r.provider ?? '–' },
    { key: 'model', label: 'Model', value: (r: Model) => r.model ?? '–', wide: true },
    { key: 'calls', label: 'Calls', value: (r: Model) => r.calls, numeric: true },
    { key: 'failures', label: 'Failed', value: (r: Model) => r.failures, numeric: true },
    { key: 'tokens', label: 'Tokens', value: (r: Model) => r.tokens, text: (r: Model) => compact(r.tokens), numeric: true },
    { key: 'avg', label: 'Avg', value: (r: Model) => r.avg_ms, text: (r: Model) => duration(r.avg_ms), numeric: true },
    { key: 'p95', label: 'p95', value: (r: Model) => r.p95_ms, text: (r: Model) => duration(r.p95_ms), numeric: true },
    { key: 'cost', label: 'Cost', value: (r: Model) => r.cost_usd, text: (r: Model) => usd(r.cost_usd), numeric: true }
  ];
  const personColumns = [
    { key: 'who', label: 'Person', value: (r: Person) => r.user_email ?? r.user_id, wide: true },
    { key: 'calls', label: 'Calls', value: (r: Person) => r.calls, numeric: true },
    { key: 'failures', label: 'Failed', value: (r: Person) => r.failures, numeric: true },
    { key: 'tokens', label: 'Tokens', value: (r: Person) => r.tokens, text: (r: Person) => compact(r.tokens), numeric: true },
    { key: 'cost', label: 'Cost', value: (r: Person) => r.cost_usd, text: (r: Person) => usd(r.cost_usd), numeric: true }
  ];
</script>

<svelte:head><title>LLM usage · Sorya Admin</title></svelte:head>

<header class="flex flex-wrap items-end justify-between gap-3">
  <div>
    <h1 class="text-2xl font-bold tracking-tight text-slate-50">LLM usage</h1>
    <p class="text-sm text-slate-400">Every AI call: script, voice and image generation.</p>
  </div>
  <div class="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5" role="radiogroup" aria-label="Time range">
    {#each RANGES as r (r.value)}
      <button type="button" role="radio" aria-checked={range === r.value} title={r.hint} class="rounded-md px-2.5 py-1 text-xs font-medium transition {range === r.value ? 'bg-slate-700 text-slate-50' : 'text-slate-400 hover:text-slate-200'}" onclick={() => setRange(r.value)}>{r.label}</button>
    {/each}
  </div>
</header>

<ErrorBanner {error} />

{#if data}
  <section class="grid grid-cols-2 gap-3 lg:grid-cols-6">
    <StatTile label="Calls" value={compact(data.totals.calls)} sub={`${data.totals.users} people`} {stale} />
    <StatTile label="Failure rate" value={percent(failRate)} sub={`${data.totals.failures} failed`} state={failRate === null ? undefined : failRate <= 0.02 ? { tone: 'good', label: 'Healthy' } : failRate <= 0.1 ? { tone: 'warning', label: 'Watch' } : { tone: 'critical', label: 'Failing' }} {stale} />
    <StatTile label="Tokens" value={compact(data.totals.tokens)} sub={`${compact(data.totals.prompt_tokens)} in · ${compact(data.totals.completion_tokens)} out`} {stale} />
    <StatTile label="Estimated cost" value={usd(data.totals.cost_usd)} sub={data.totals.cost_usd === null ? 'No prices set (TELEMETRY_PRICES)' : undefined} {stale} />
    <StatTile label="Average call" value={duration(data.totals.avg_ms)} {stale} />
    <StatTile label="Slowest 5%" value={duration(data.totals.p95_ms)} sub="p95" {stale} />
  </section>

  <div class="grid gap-3 lg:grid-cols-2">
    <TimeChart title="Calls" subtitle="Failures in red" points={calls} series={[{ key: 'ok', label: 'Succeeded', color: 'var(--series-1)', type: 'bar' }, { key: 'failed', label: 'Failed', color: 'var(--status-critical)', type: 'bar' }]} {stale} />
    <TimeChart title="Tokens" points={tokens} series={[{ key: 'tokens', label: 'Tokens', color: 'var(--series-1)', type: 'bar' }]} {stale} />
  </div>
  <TimeChart title="Estimated cost" subtitle="USD per time bucket" points={cost} series={[{ key: 'cost', label: 'Cost', color: 'var(--series-1)', type: 'line', area: true }]} format={usd} integers={false} {stale} emptyText="No cost recorded. Set TELEMETRY_PRICES to price calls." />

  <DataTable title="By model" rows={data.by_model} columns={modelColumns} id={(r) => `${r.call}|${r.provider}|${r.model}`} initialSort={{ key: 'calls', dir: 'desc' }} {stale} emptyText="No AI calls in this range." />
  <DataTable title="By person" subtitle="Top 25 by calls" rows={data.by_user} columns={personColumns} id={(r) => r.user_id} initialSort={{ key: 'calls', dir: 'desc' }} {stale} emptyText="No signed-in AI usage in this range.">
    {#snippet detail(r: Person)}
      <a class="text-xs font-semibold text-sun-300 hover:text-sun-200" href="/users/{r.user_id}">Open this person →</a>
    {/snippet}
  </DataTable>

  <section class="rounded-xl border border-slate-800 bg-[var(--viz-surface)]">
    <header class="border-b border-[var(--viz-grid)] px-4 py-2.5"><h3 class="text-sm font-semibold text-[var(--viz-ink)]">Latest failures</h3></header>
    <EventList events={data.recent_failures} emptyText="No failed AI calls in this range." />
  </section>
{:else if !error}
  <p class="py-16 text-center text-sm text-slate-400">Loading…</p>
{/if}
