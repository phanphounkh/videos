<script lang="ts">
  /** The project's uploaded pictures and clips, ready to reuse. */
  import Button from '$lib/components/ui/Button.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import type { MediaAsset } from '$lib/types/api';

  let {
    media,
    hasScene,
    onupload,
    onuse,
    onaddscene
  }: {
    media: MediaAsset[];
    /** Whether a scene is selected to receive the media. */
    hasScene: boolean;
    onupload: (file: File) => void;
    onuse: (asset: MediaAsset) => void;
    onaddscene: (asset: MediaAsset) => void;
  } = $props();

  let fileInput = $state<HTMLInputElement>();
  let over = $state(false);

  const visual = $derived(media.filter((asset) => asset.type === 'image' || asset.type === 'video'));
  const clock = (seconds: number | null) =>
    seconds ? `${Math.floor(seconds / 60)}:${String(Math.round(seconds % 60)).padStart(2, '0')}` : '';

  function drop(event: DragEvent) {
    event.preventDefault();
    over = false;
    for (const file of event.dataTransfer?.files ?? []) onupload(file);
  }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
  class="flex flex-col gap-3 rounded-xl border border-dashed p-2.5 transition {over
    ? 'border-sun-400 bg-sun-500/10'
    : 'border-slate-800'}"
  ondragover={(e) => {
    e.preventDefault();
    over = true;
  }}
  ondragleave={() => (over = false)}
  ondrop={drop}
>
  <Button variant="secondary" icon="upload" onclick={() => fileInput?.click()}>
    Upload pictures or clips
  </Button>
  <input
    bind:this={fileInput}
    type="file"
    multiple
    accept="image/png,image/jpeg,image/webp,video/mp4,video/webm,.png,.jpg,.jpeg,.webp,.mp4,.webm"
    class="hidden"
    onchange={(e) => {
      for (const file of e.currentTarget.files ?? []) onupload(file);
      e.currentTarget.value = '';
    }}
  />

  {#if !visual.length}
    <div class="flex flex-col items-center gap-2 px-3 py-8 text-center">
      <span class="grid h-10 w-10 place-items-center rounded-full bg-slate-800 text-slate-400">
        <Icon name="image" size={18} />
      </span>
      <p class="text-sm font-medium text-slate-300">Your media lives here</p>
      <p class="text-xs leading-relaxed text-slate-500">
        Drop pictures or clips on this panel. They stay in the project, so you can use them in
        any scene.
      </p>
    </div>
  {/if}

  <div class="grid grid-cols-2 gap-2">
    {#each visual as asset (asset.id)}
      <div class="flex flex-col gap-1.5 rounded-xl border border-slate-800 bg-slate-900/50 p-1.5">
        <div class="relative aspect-video overflow-hidden rounded bg-slate-950">
          {#if asset.type === 'video'}
            <!-- svelte-ignore a11y_media_has_caption -->
            <video
              src={`${asset.url}#t=0.1`}
              preload="metadata"
              muted
              class="h-full w-full object-cover"
            ></video>
            <span class="absolute right-1 bottom-1 rounded bg-black/70 px-1 text-[10px]">
              {clock(asset.duration)}
            </span>
          {:else}
            <img src={asset.url} alt="" class="h-full w-full object-cover" loading="lazy" />
          {/if}
        </div>
        <p class="truncate text-[10px] text-slate-400" title={asset.original_filename ?? ''}>
          {asset.original_filename}
        </p>
        <div class="flex gap-1">
          <button
            class="flex-1 rounded-md bg-[image:var(--sun-gradient)] px-1 py-1 text-[11px] font-semibold text-sun-950 hover:brightness-110 disabled:opacity-40"
            disabled={!hasScene}
            title={hasScene ? 'Use in the selected scene' : 'Select a scene first'}
            onclick={() => onuse(asset)}>Use here</button
          >
          <button
            class="flex-1 rounded-md bg-slate-800 px-1 py-1 text-[11px] font-medium hover:bg-slate-700"
            title="Add as a new scene after the playhead"
            onclick={() => onaddscene(asset)}>+ Scene</button
          >
        </div>
      </div>
    {/each}
  </div>
</div>
