<script lang="ts">
  import type { Caption } from '$lib/types/api';

  /** Read-only caption inspector: timings come from the narration + audio. */
  let { captions }: { captions: Caption[] } = $props();
</script>

<div class="flex flex-col gap-1">
  {#if captions.length}
    {#each captions as caption (caption.id)}
      <div class="flex gap-2 rounded border border-slate-800 bg-slate-950/60 px-2 py-1 text-xs">
        <span class="w-24 shrink-0 font-mono text-slate-500">
          {caption.start_time.toFixed(2)}–{caption.end_time.toFixed(2)}
        </span>
        <span class="flex-1" class:km={caption.language.startsWith('km')}>{caption.text}</span>
      </div>
    {/each}
  {:else}
    <p class="text-xs text-slate-500">
      No captions yet. They are generated from the narration text.
    </p>
  {/if}
</div>
