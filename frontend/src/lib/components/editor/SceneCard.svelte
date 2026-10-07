<script lang="ts">
  import type { Scene } from '$lib/types/api';

  let {
    scene,
    selected = false,
    onselect,
    onmoveup,
    onmovedown
  }: {
    scene: Scene;
    selected?: boolean;
    onselect: (id: string) => void;
    onmoveup: (id: string) => void;
    onmovedown: (id: string) => void;
  } = $props();
</script>

<div
  class="flex gap-2 rounded-lg border p-2 transition {selected
    ? 'border-indigo-500 bg-indigo-500/10'
    : 'border-slate-800 bg-slate-900/40 hover:border-slate-700'}"
>
  <button class="flex flex-1 gap-2 text-left" onclick={() => onselect(scene.id)}>
    <div class="h-12 w-20 shrink-0 overflow-hidden rounded bg-slate-950">
      {#if scene.image_url}
        <img src={scene.image_url} alt="" class="h-full w-full object-cover" loading="lazy" />
      {:else}
        <div class="flex h-full items-center justify-center text-[10px] text-slate-600">
          no image
        </div>
      {/if}
    </div>
    <div class="min-w-0 flex-1">
      <p class="text-xs text-slate-400">
        #{scene.scene_number} · {scene.duration.toFixed(1)}s
        {#if scene.audio_url}<span class="text-emerald-400"> · voice</span>{/if}
      </p>
      <p class="truncate text-sm">{scene.on_screen_text || scene.narration || '(empty)'}</p>
    </div>
  </button>

  <div class="flex flex-col gap-1">
    <button
      class="rounded px-1 text-xs text-slate-400 hover:bg-slate-800"
      title="Move up"
      onclick={() => onmoveup(scene.id)}>▲</button
    >
    <button
      class="rounded px-1 text-xs text-slate-400 hover:bg-slate-800"
      title="Move down"
      onclick={() => onmovedown(scene.id)}>▼</button
    >
  </div>
</div>
