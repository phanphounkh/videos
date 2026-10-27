<script lang="ts">
  import Icon from '$lib/components/ui/Icon.svelte';
  /** Severity as an icon plus a word for the loud levels, a quiet word for the rest. */
  let { level }: { level: string } = $props();
</script>

{#if level === 'error'}
  <span class="inline-flex items-center gap-1 text-xs font-medium" style="color:var(--status-critical)">
    <Icon name="alert" size={12} /> error
  </span>
{:else if level === 'warning'}
  <span class="inline-flex items-center gap-1 text-xs font-medium" style="color:var(--status-warning)">
    <Icon name="alert" size={12} /> warning
  </span>
{:else}
  <span class="text-xs text-[var(--viz-ink-3)]">{level}</span>
{/if}
