<script lang="ts">
  /**
   * Is telemetry itself working? This is how to tell "nothing is happening" from "the
   * consumer died": the database, Redis, the stream's backlog, and what the consumer has
   * done since it started.
   */
  import StatTile from '$lib/components/telemetry/StatTile.svelte';
  import { ago, compact } from '$lib/components/telemetry/format';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import { admin, type Health } from '$lib/telemetry/admin';
  import { auth } from '$lib/stores/auth.svelte';

  let data = $state<Health | null>(null);
  let error = $state<unknown>(null);

  async function load() {
    try {
      data = await admin.health();
      error = null;
    } catch (e) {
      error = e;
    }
  }
  $effect(() => {
    if (!auth.user?.is_admin) return;
    void load();
    const timer = setInterval(() => void load(), 10_000);
    return () => clearInterval(timer);
  });

  const ok = (good: boolean, label: string, bad = 'Down') =>
    good ? { tone: 'good' as const, label } : { tone: 'critical' as const, label: bad };
  const consumer = $derived(data?.consumer ?? {});
  const num = (k: string) => (typeof consumer[k] === 'number' ? (consumer[k] as number) : null);
</script>

<svelte:head><title>Health · Sorya Admin</title></svelte:head>

<header>
  <h1 class="text-2xl font-bold tracking-tight text-slate-50">Health</h1>
  <p class="text-sm text-slate-400">Is telemetry itself working?</p>
</header>

<ErrorBanner {error} />

{#if data}
  <section class="grid grid-cols-2 gap-3 lg:grid-cols-4">
    <StatTile label="Overall" value={data.status === 'ok' ? 'Healthy' : 'Degraded'} state={ok(data.status === 'ok', 'All systems working', 'Needs attention')} />
    <StatTile label="Database" value={data.database.ok ? 'Connected' : 'Down'} sub={data.database.error} state={ok(data.database.ok, 'Reachable')} />
    <StatTile label="Redis" value={data.redis.ok ? 'Connected' : 'Down'} sub={data.redis.error} state={ok(data.redis.ok, 'Reachable')} />
    <StatTile label="Event consumer" value={String(consumer.state ?? 'unknown')} state={ok(consumer.state === 'live', 'Reading the stream', 'Not reading')} />
    <StatTile label="Stored events" value={compact(data.stored.events ?? 0)} sub={data.stored.last_event_at ? `latest ${ago(data.stored.last_event_at)}` : 'none yet'} />
    <StatTile label="Stream length" value={compact(data.redis.stream_length ?? 0)} sub="Events in Redis, waiting or recently read" />
    <StatTile label="Waiting to be stored" value={compact(data.redis.pending ?? 0)} state={(data.redis.pending ?? 0) > 1000 ? { tone: 'warning', label: 'Backlog' } : { tone: 'good', label: 'Keeping up' }} />
    <StatTile label="Stored since start" value={num('persisted') === null ? '–' : compact(num('persisted'))} sub={num('rejected') ? `${num('rejected')} refused by the database` : undefined} />
    <StatTile label="Malformed events" value={compact(num('dropped') ?? 0)} sub="Could not be read; non-zero usually means the backend and service disagree on the event shape" state={(num('dropped') ?? 0) > 0 ? { tone: 'warning', label: 'Check the shape' } : { tone: 'good', label: 'None' }} />
  </section>

  <section class="rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4">
    <h3 class="mb-2 text-sm font-semibold text-[var(--viz-ink)]">Consumer detail</h3>
    <pre class="overflow-auto text-[11px] leading-relaxed text-[var(--viz-ink-2)]">{JSON.stringify(data.consumer, null, 2)}</pre>
  </section>
{:else if !error}
  <p class="py-16 text-center text-sm text-slate-400">Checking…</p>
{/if}
