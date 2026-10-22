<script lang="ts">
  import Icon from '$lib/components/ui/Icon.svelte';
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
  class="group relative flex gap-2.5 rounded-xl border p-2 transition {selected
    ? 'border-sun-400/70 bg-sun-400/[0.07]'
    : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900'}"
>
  <button class="flex min-w-0 flex-1 gap-2.5 text-left" onclick={() => onselect(scene.id)}>
    <div class="relative h-12 w-[5.25rem] shrink-0 overflow-hidden rounded-md bg-slate-950">
      {#if scene.image_url}
        <img src={scene.image_url} alt="" class="h-full w-full object-cover" loading="lazy" />
      {:else if scene.video_url}
        <!-- svelte-ignore a11y_media_has_caption -->
        <video src={`${scene.video_url}#t=0.1`} preload="metadata" muted class="h-full w-full object-cover"></video>
      {:else}
        <div class="grid h-full place-items-center text-slate-600"><Icon name="film" size={16} /></div>
      {/if}
      <span class="absolute bottom-0.5 left-0.5 rounded bg-black/65 px-1 text-[10px] font-semibold text-white">
        {scene.scene_number}
      </span>
    </div>
    <div class="flex min-w-0 flex-1 flex-col justify-center gap-0.5">
      <p class="line-clamp-2 text-[13px] leading-snug font-medium text-slate-100">
        {scene.on_screen_text || scene.narration || '(empty scene)'}
      </p>
      <p class="flex items-center gap-2 text-[11px] text-slate-500">
        <span class="inline-flex items-center gap-1"><Icon name="clock" size={11} />{scene.duration.toFixed(1)}s</span>
        {#if scene.audio_url}
          <span class="inline-flex items-center gap-1 text-emerald-400"><Icon name="mic" size={11} />voice</span>
        {/if}
        {#if scene.video_url}
          <span class="inline-flex items-center gap-1 text-sky-400"><Icon name="video" size={11} />clip</span>
        {/if}
      </p>
    </div>
  </button>

  <div
    class="absolute top-1.5 right-1.5 flex flex-col rounded-md bg-slate-950/80 opacity-0 backdrop-blur transition group-focus-within:opacity-100 group-hover:opacity-100"
  >
    <button
      class="grid h-5 w-5 place-items-center rounded text-slate-400 hover:bg-slate-700 hover:text-white"
      title="Move up"
      aria-label="Move scene up"
      onclick={() => onmoveup(scene.id)}><Icon name="chevronUp" size={13} /></button
    >
    <button
      class="grid h-5 w-5 place-items-center rounded text-slate-400 hover:bg-slate-700 hover:text-white"
      title="Move down"
      aria-label="Move scene down"
      onclick={() => onmovedown(scene.id)}><Icon name="chevronDown" size={13} /></button
    >
  </div>
</div>
