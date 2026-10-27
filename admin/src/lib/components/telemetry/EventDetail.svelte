<script lang="ts">
  import { clock, shortId, summary, who, type TEvent } from '$lib/telemetry/admin';
  import { duration } from '$lib/components/telemetry/format';
  import SourceBadge from '$lib/components/telemetry/SourceBadge.svelte';

  let { event, related = [], loading = false }: { event: TEvent; related?: TEvent[]; loading?: boolean } = $props();

  const facts = $derived(
    (
      [
        ['Event id', event.id],
        ['Time', new Date(event.created_at).toISOString()],
        ['Type', event.event_type],
        ['Outcome', event.outcome],
        ['Path', event.path],
        ['Duration', event.duration_ms === null ? null : duration(event.duration_ms)],
        ['Provider', event.provider],
        ['Model', event.model],
        ['Tokens', event.total_tokens === null ? null : `${event.prompt_tokens ?? 0} in + ${event.completion_tokens ?? 0} out`],
        ['Cost', event.cost_usd === null ? null : `$${event.cost_usd}`],
        ['Client', [event.platform, event.os, event.browser].filter(Boolean).join(' · ') || null]
      ] as [string, string | null][]
    ).filter(([, v]) => v)
  );
  const json = $derived(JSON.stringify(event.properties, null, 2));
</script>

<div class="grid gap-4 lg:grid-cols-2">
  <div class="min-w-0 space-y-3">
    <dl class="grid grid-cols-[7rem_1fr] gap-x-3 gap-y-1 text-xs">
      {#each facts as [label, value] (label)}
        <dt class="text-[var(--viz-ink-3)]">{label}</dt>
        <dd class="min-w-0 break-all text-[var(--viz-ink)]">{value}</dd>
      {/each}
      <dt class="text-[var(--viz-ink-3)]">Who</dt>
      <dd class="text-[var(--viz-ink)]">
        {who(event)}
        {#if event.user_id}
          · <a class="text-sun-300 hover:text-sun-200" href="/users/{event.user_id}">user page</a>
          · <a class="text-sun-300 hover:text-sun-200" href="/events?user={event.user_id}">all events</a>
        {/if}
      </dd>
      {#if event.session_id}
        <dt class="text-[var(--viz-ink-3)]">Session</dt>
        <dd class="text-[var(--viz-ink)]">
          {shortId(event.session_id)} ·
          <a class="text-sun-300 hover:text-sun-200" href="/sessions/{event.session_id}">timeline</a>
          · <a class="text-sun-300 hover:text-sun-200" href="/events?session={event.session_id}">events</a>
        </dd>
      {/if}
      {#if event.request_id}
        <dt class="text-[var(--viz-ink-3)]">Request</dt>
        <dd class="text-[var(--viz-ink)]">
          {shortId(event.request_id)} ·
          <a class="text-sun-300 hover:text-sun-200" href="/events?request_id={event.request_id}&range=90d">everything for this request</a>
        </dd>
      {/if}
    </dl>

    {#if related.length}
      <div>
        <h4 class="mb-1 text-xs font-semibold text-[var(--viz-ink-2)]">Same request ({related.length})</h4>
        <ul class="space-y-1">
          {#each related as r (r.id)}
            <li class="flex items-center gap-2 text-xs">
              <span class="text-[var(--viz-ink-3)] tabular-nums">{clock(r.created_at)}</span>
              <SourceBadge source={r.source} />
              <span class="font-medium text-[var(--viz-ink)]">{r.name}</span>
              <span class="truncate text-[var(--viz-ink-2)]">{summary(r)}</span>
            </li>
          {/each}
        </ul>
      </div>
    {:else if loading}
      <p class="text-xs text-[var(--viz-ink-3)]">Looking for related events…</p>
    {/if}
  </div>

  <div class="min-w-0">
    <h4 class="mb-1 text-xs font-semibold text-[var(--viz-ink-2)]">Properties</h4>
    <pre class="max-h-72 overflow-auto rounded-lg border border-[var(--viz-grid)] bg-[var(--viz-surface)] p-3 text-[11px] leading-relaxed text-[var(--viz-ink-2)]">{json}</pre>
  </div>
</div>
