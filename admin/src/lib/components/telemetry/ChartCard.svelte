<script lang="ts">
  /** The frame every chart sits in: title, subtitle, and the Chart / Table switch. */
  let {
    title,
    subtitle = undefined,
    mode = $bindable<'chart' | 'table'>('chart'),
    stale = false,
    chart,
    table,
    actions = undefined
  }: {
    title: string;
    subtitle?: string;
    mode?: 'chart' | 'table';
    /** Data is being refetched: keep the old render, dimmed, instead of a flash. */
    stale?: boolean;
    chart: import('svelte').Snippet;
    table: import('svelte').Snippet;
    actions?: import('svelte').Snippet;
  } = $props();
</script>

<section class="min-w-0 rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4">
  <header class="mb-3 flex items-start justify-between gap-3">
    <div class="min-w-0">
      <h3 class="text-sm font-semibold text-[var(--viz-ink)]">{title}</h3>
      {#if subtitle}<p class="mt-0.5 text-xs text-[var(--viz-ink-3)]">{subtitle}</p>{/if}
    </div>
    <div class="flex shrink-0 items-center gap-2">
      {@render actions?.()}
      <div class="inline-flex rounded-lg border border-slate-800 p-0.5 text-xs" role="group" aria-label="View">
        {#each ['chart', 'table'] as const as option (option)}
          <button
            type="button"
            class="rounded-md px-2 py-1 font-medium capitalize transition {mode === option
              ? 'bg-slate-800 text-slate-50'
              : 'text-slate-400 hover:text-slate-200'}"
            aria-pressed={mode === option}
            onclick={() => (mode = option)}>{option}</button
          >
        {/each}
      </div>
    </div>
  </header>
  <div class="transition-opacity duration-200 {stale ? 'opacity-50' : ''}">
    {#if mode === 'chart'}{@render chart()}{:else}{@render table()}{/if}
  </div>
</section>
