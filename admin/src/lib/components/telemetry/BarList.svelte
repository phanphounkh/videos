<script lang="ts">
  /**
   * Ranked horizontal bars for a nominal category (events, endpoints, purposes).
   * One series, so one colour for every bar: the bar's length already says how
   * much, and colouring by value would spend the colour channel saying it twice.
   * The value sits at the bar tip; the category name is plain text beside it.
   */
  import ChartCard from '$lib/components/telemetry/ChartCard.svelte';
  import { compact } from '$lib/components/telemetry/format';

  let {
    title,
    subtitle = undefined,
    rows,
    valueLabel = 'Count',
    format = compact,
    stale = false,
    emptyText = 'Nothing recorded in this range.'
  }: {
    title: string;
    subtitle?: string;
    rows: { label: string; value: number; extra?: string }[];
    valueLabel?: string;
    format?: (v: number) => string;
    stale?: boolean;
    emptyText?: string;
  } = $props();

  let mode = $state<'chart' | 'table'>('chart');
  let focused = $state<number | null>(null);
  const max = $derived(Math.max(...rows.map((r) => r.value), 1));
  const total = $derived(rows.reduce((sum, r) => sum + r.value, 0));
</script>

<ChartCard {title} {subtitle} bind:mode {stale}>
  {#snippet chart()}
    {#if !rows.length}
      <p class="py-8 text-center text-xs text-[var(--viz-ink-3)]">{emptyText}</p>
    {:else}
      <ul class="flex flex-col gap-1.5">
        {#each rows as row, index (row.label)}
          <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
          <li
            class="group relative grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-3 rounded-md px-1.5 py-1 outline-offset-0 hover:bg-slate-800/40 focus:bg-slate-800/40"
            tabindex="0"
            onfocus={() => (focused = index)}
            onblur={() => (focused = null)}
            aria-label={`${row.label}: ${format(row.value)} ${valueLabel.toLowerCase()}`}
          >
            <span class="truncate text-xs text-[var(--viz-ink-2)]" title={row.label}>{row.label}</span>
            <span class="relative block h-3.5">
              <span
                class="absolute inset-y-0 left-0 rounded-r-[4px]"
                style="width:max({(row.value / max) * 100}%, 2px); background:var(--series-1)"
              ></span>
            </span>
            <span class="min-w-8 text-right text-xs font-semibold text-[var(--viz-ink)] tabular-nums">
              {format(row.value)}
            </span>
            <span
              class="pointer-events-none absolute right-0 bottom-full z-10 mb-1 hidden rounded-lg border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-pop group-hover:block {focused ===
              index
                ? '!block'
                : ''}"
            >
              <span class="font-semibold text-[var(--viz-ink)] tabular-nums">{format(row.value)}</span>
              <span class="text-[var(--viz-ink-2)]">
                {valueLabel.toLowerCase()} · {Math.round((row.value / (total || 1)) * 100)}% of shown</span
              >
              {#if row.extra}<span class="block text-[var(--viz-ink-3)]">{row.extra}</span>{/if}
            </span>
          </li>
        {/each}
      </ul>
    {/if}
  {/snippet}

  {#snippet table()}
    <div class="max-h-64 overflow-auto rounded-lg border border-slate-800">
      <table class="w-full text-left text-xs">
        <thead class="sticky top-0 bg-slate-900 text-[var(--viz-ink-3)]">
          <tr>
            <th class="px-3 py-2 font-medium">Name</th>
            <th class="px-3 py-2 text-right font-medium">{valueLabel}</th>
            <th class="px-3 py-2 text-right font-medium">Share</th>
          </tr>
        </thead>
        <tbody class="text-[var(--viz-ink)] tabular-nums">
          {#each rows as row (row.label)}
            <tr class="border-t border-slate-800/70">
              <td class="px-3 py-1.5 text-[var(--viz-ink-2)]">{row.label}</td>
              <td class="px-3 py-1.5 text-right">{format(row.value)}</td>
              <td class="px-3 py-1.5 text-right">{Math.round((row.value / (total || 1)) * 100)}%</td>
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/snippet}
</ChartCard>
