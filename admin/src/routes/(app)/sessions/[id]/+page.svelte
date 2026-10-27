<script lang="ts">
  /**
   * One session, in order: what the person did in the browser and what the server did
   * because of it, interleaved. Server events sit indented under the browser event that
   * caused them when they share a request id.
   */
  import { page } from '$app/state';
  import { duration } from '$lib/components/telemetry/format';
  import EventList from '$lib/components/telemetry/EventList.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import { admin, clock, shortId, type SessionTimeline, type TEvent } from '$lib/telemetry/admin';
  import { auth } from '$lib/stores/auth.svelte';

  const id = $derived(page.params.id ?? '');
  let timeline = $state<SessionTimeline | null>(null);
  let error = $state<unknown>(null);
  let show = $state<'all' | 'frontend' | 'server' | 'errors'>('all');
  // The "noise" the person usually does not want in a timeline.
  let quiet = $state(true);
  const NOISY = new Set(['scroll_depth', 'visibility', 'long_task', 'web_vital', 'input_change']);

  $effect(() => {
    if (!auth.user?.is_admin || !id) return;
    timeline = null;
    admin
      .timeline(id)
      .then((t) => ((timeline = t), (error = null)))
      .catch((e) => (error = e));
  });

  const events = $derived.by(() => {
    const all = timeline?.events ?? [];
    return all.filter((e: TEvent) => {
      if (quiet && NOISY.has(e.name)) return false;
      if (show === 'frontend') return e.source === 'frontend';
      if (show === 'server') return e.source !== 'frontend';
      if (show === 'errors') return e.level === 'error' || e.level === 'warning';
      return true;
    });
  });
  const length = $derived(
    timeline ? new Date(timeline.last_seen).getTime() - new Date(timeline.first_seen).getTime() : 0
  );
  const pages = $derived((timeline?.events ?? []).filter((e) => e.name === 'page_view').length);
  const errors = $derived((timeline?.events ?? []).filter((e) => e.level === 'error').length);
</script>

<div class="flex flex-wrap items-center gap-2 text-sm">
  <a href="/sessions" class="text-sun-300 hover:text-sun-200">← Sessions</a>
  <span class="text-slate-500">/</span>
  <span class="font-semibold text-slate-100">{shortId(id)}</span>
</div>

<ErrorBanner {error} />

{#if timeline}
  <section class="grid grid-cols-2 gap-3 sm:grid-cols-5">
    {#each [['Who', timeline.user_email ?? (timeline.user_id ? shortId(timeline.user_id) : 'Signed out')], ['Started', new Date(timeline.first_seen).toLocaleString()], ['Length', duration(length)], ['Pages', String(pages)], ['Errors', String(errors)]] as [label, value] (label)}
      <div class="rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-3">
        <p class="text-xs text-[var(--viz-ink-3)]">{label}</p>
        <p class="mt-0.5 truncate text-sm font-semibold text-[var(--viz-ink)]">
          {#if label === 'Who' && timeline.user_id}
            <a class="text-sun-300 hover:text-sun-200" href="/users/{timeline.user_id}">{value}</a>
          {:else}{value}{/if}
        </p>
      </div>
    {/each}
  </section>

  <div class="flex flex-wrap items-center gap-3">
    <div class="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5" role="radiogroup" aria-label="Show">
      {#each [['all', 'Everything'], ['frontend', 'Browser'], ['server', 'Server'], ['errors', 'Problems']] as [value, label] (value)}
        <button type="button" role="radio" aria-checked={show === value} class="rounded-md px-2.5 py-1 text-xs font-medium transition {show === value ? 'bg-slate-700 text-slate-50' : 'text-slate-400 hover:text-slate-200'}" onclick={() => (show = value as typeof show)}>{label}</button>
      {/each}
    </div>
    <label class="inline-flex cursor-pointer items-center gap-2 text-xs text-slate-300">
      <input type="checkbox" bind:checked={quiet} /> Hide scrolls, vitals and typing
    </label>
    <span class="text-xs text-slate-400">{events.length} of {timeline.events.length} events · started {clock(timeline.first_seen)}</span>
  </div>

  <section class="rounded-xl border border-slate-800 bg-[var(--viz-surface)]">
    <EventList {events} emptyText="Nothing to show with these options." />
  </section>
{:else if !error}
  <p class="py-16 text-center text-sm text-slate-400">Loading the session…</p>
{/if}
