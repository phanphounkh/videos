<script lang="ts">
  /** Where an event came from. A coloured dot AND the word: colour never says it alone. */
  let { source }: { source: string } = $props();
  const color: Record<string, string> = {
    frontend: 'var(--series-1)',
    backend: 'var(--series-2)',
    worker: 'var(--series-3)'
  };
</script>

<span class="inline-flex items-center gap-1.5 text-xs text-[var(--viz-ink-2)]">
  <span class="h-2 w-2 shrink-0 rounded-full" style="background:{color[source] ?? 'var(--viz-ink-3)'}"></span>
  {source}
</span>
