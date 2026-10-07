<script lang="ts">
  let { name, children }: { name: string; children?: import('svelte').Snippet } = $props();
</script>

<div class="flex items-stretch gap-2">
  <span class="w-16 shrink-0 self-center text-[10px] tracking-wide text-slate-500 uppercase">
    {name}
  </span>
  <div class="relative h-9 flex-1 rounded border border-slate-800 bg-slate-950/70">
    {@render children?.()}
  </div>
</div>
