<script lang="ts">
  /** Label + control wrapper so every form looks the same. */
  let {
    label,
    hint = undefined,
    children
  }: { label: string; hint?: string; children?: import('svelte').Snippet } = $props();
</script>

<label class="flex flex-col gap-1.5">
  <span class="text-xs font-medium tracking-wide text-slate-400 uppercase">{label}</span>
  {@render children?.()}
  {#if hint}
    <span class="text-xs text-slate-500">{hint}</span>
  {/if}
</label>
