<script lang="ts">
  /**
   * Events as a dense, scannable list. A row opens to everything the event knows, plus
   * the other events that share its request (the browser's call and the server's work).
   */
  import { admin, clock, day, shortId, summary, who, type TEvent } from '$lib/telemetry/admin';
  import { duration } from '$lib/components/telemetry/format';
  import EventDetail from '$lib/components/telemetry/EventDetail.svelte';
  import LevelMark from '$lib/components/telemetry/LevelMark.svelte';
  import SourceBadge from '$lib/components/telemetry/SourceBadge.svelte';

  let {
    events,
    fresh = new Set<string>(),
    emptyText = 'No events match.',
    /** Show the day when it changes between rows (for lists that span days). */
    days = true
  }: { events: TEvent[]; fresh?: Set<string>; emptyText?: string; days?: boolean } = $props();

  let open = $state<string | null>(null);
  let detail = $state<{ event: TEvent; same_request: TEvent[] } | null>(null);
  let loading = $state(false);

  async function toggle(e: TEvent) {
    if (open === e.id) {
      open = null;
      return;
    }
    open = e.id;
    detail = null;
    loading = true;
    try {
      const result = await admin.event(e.id);
      if (open === e.id) detail = result;
    } catch {
      if (open === e.id) detail = { event: e, same_request: [] };
    } finally {
      loading = false;
    }
  }
</script>

{#if !events.length}
  <p class="py-12 text-center text-sm text-[var(--viz-ink-3)]">{emptyText}</p>
{:else}
  <div class="overflow-x-auto">
    <table class="w-full min-w-[820px] border-collapse text-left text-xs">
      <thead class="text-[var(--viz-ink-3)]">
        <tr class="border-b border-[var(--viz-grid)]">
          <th class="w-28 px-3 py-2 font-medium">Time</th>
          <th class="w-24 px-3 py-2 font-medium">Source</th>
          <th class="w-20 px-3 py-2 font-medium">Level</th>
          <th class="px-3 py-2 font-medium">Event</th>
          <th class="px-3 py-2 font-medium">Detail</th>
          <th class="w-40 px-3 py-2 font-medium">Who</th>
          <th class="w-20 px-3 py-2 text-right font-medium">Took</th>
        </tr>
      </thead>
      <tbody>
        {#each events as e, i (e.id)}
          {#if days && (i === 0 || day(events[i - 1].created_at) !== day(e.created_at))}
            <tr><td colspan="7" class="bg-slate-900/60 px-3 py-1 text-[11px] font-semibold text-[var(--viz-ink-3)]">{day(e.created_at)}</td></tr>
          {/if}
          <tr
            class="cursor-pointer border-b border-[var(--viz-grid)] transition hover:bg-slate-800/40 {open === e.id ? 'bg-slate-800/50' : ''} {fresh.has(e.id) ? 'flash-new' : ''}"
            onclick={() => toggle(e)}
            onkeydown={(k) => (k.key === 'Enter' || k.key === ' ') && (k.preventDefault(), toggle(e))}
            tabindex="0"
            aria-expanded={open === e.id}
          >
            <td class="px-3 py-1.5 whitespace-nowrap text-[var(--viz-ink-2)] tabular-nums">{clock(e.created_at)}</td>
            <td class="px-3 py-1.5"><SourceBadge source={e.source} /></td>
            <td class="px-3 py-1.5"><LevelMark level={e.level} /></td>
            <td class="px-3 py-1.5 font-medium whitespace-nowrap text-[var(--viz-ink)]">{e.name}</td>
            <td class="max-w-[28rem] truncate px-3 py-1.5 text-[var(--viz-ink-2)]" title={summary(e)}>{summary(e)}</td>
            <td class="max-w-40 truncate px-3 py-1.5 text-[var(--viz-ink-2)]" title={e.user_id ?? ''}>{who(e)}</td>
            <td class="px-3 py-1.5 text-right whitespace-nowrap text-[var(--viz-ink-2)] tabular-nums">{e.duration_ms === null ? '' : duration(e.duration_ms)}</td>
          </tr>
          {#if open === e.id}
            <tr class="border-b border-[var(--viz-grid)] bg-slate-950/60">
              <td colspan="7" class="px-4 py-3">
                <EventDetail event={detail?.event ?? e} related={detail?.same_request ?? []} {loading} />
              </td>
            </tr>
          {/if}
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<style>
  .flash-new {
    animation: flash 1.4s ease-out;
  }
  @keyframes flash {
    from { background: rgb(57 135 229 / 0.25); }
    to { background: transparent; }
  }
</style>
