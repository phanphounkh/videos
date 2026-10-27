<script lang="ts">
  /** The project's uploaded pictures and clips, ready to reuse. */
  import Button from '$lib/components/ui/Button.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Segmented from '$lib/components/ui/Segmented.svelte';
  import { t } from '$lib/i18n/index.svelte';
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
  let sub = $state<'project' | 'uploads'>('project');
  let query = $state('');

  const visual = $derived(media.filter((asset) => asset.type === 'image' || asset.type === 'video'));
  const shown = $derived(
    visual.filter((asset) =>
      (asset.original_filename ?? '').toLowerCase().includes(query.trim().toLowerCase())
    )
  );
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
  class="flex flex-col gap-3 rounded-xl transition {over ? 'bg-sun-500/10 ring-2 ring-sun-400' : ''}"
  ondragover={(e) => {
    e.preventDefault();
    over = true;
  }}
  ondragleave={() => (over = false)}
  ondrop={drop}
>
  <Segmented
    label={t('editor.media.source')}
    options={[
      { value: 'project', label: t('editor.media.project') },
      { value: 'uploads', label: t('editor.media.uploads') }
    ]}
    bind:value={sub}
  />

  <Button icon="upload" onclick={() => fileInput?.click()}>{t('editor.media.import')}</Button>
  <input
    bind:this={fileInput}
    type="file"
    multiple
    accept="image/png,image/jpeg,image/webp,video/mp4,video/webm,.png,.jpg,.jpeg,.webp,.mp4,.webm"
    class="hidden"
    onchange={(e) => {
      for (const file of e.currentTarget.files ?? []) onupload(file);
      e.currentTarget.value = '';
      sub = 'project';
    }}
  />

  {#if sub === 'uploads'}
    <button
      class="flex flex-col items-center gap-2 rounded-xl border border-dashed border-slate-700 px-3 py-10 text-center transition hover:border-sun-400/60 hover:bg-slate-900"
      onclick={() => fileInput?.click()}
    >
      <span class="grid h-10 w-10 place-items-center rounded-full bg-slate-800 text-slate-400">
        <Icon name="upload" size={18} />
      </span>
      <span class="text-sm font-medium text-slate-300">{t('editor.media.drop')}</span>
      <span class="text-xs leading-relaxed text-slate-500">
        {t('editor.media.dropHint')}
      </span>
    </button>
  {:else}
    <label class="relative block">
      <Icon name="search" size={14} class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500" />
      <input
        type="search"
        bind:value={query}
        placeholder={t('editor.media.search')}
        aria-label={t('editor.media.search')}
        class="w-full !pl-9 px-3 py-2 text-sm"
      />
    </label>

    {#if !visual.length}
      <div class="flex flex-col items-center gap-2 px-3 py-8 text-center">
        <span class="grid h-10 w-10 place-items-center rounded-full bg-slate-800 text-slate-400">
          <Icon name="image" size={18} />
        </span>
        <p class="text-sm font-medium text-slate-300">{t('editor.media.emptyTitle')}</p>
        <p class="text-xs leading-relaxed text-slate-500">
          {t('editor.media.emptyHint')}
        </p>
      </div>
    {:else if !shown.length}
      <p class="py-6 text-center text-sm text-slate-500">{t('editor.media.noMatch', { query })}</p>
    {/if}

    <div class="grid grid-cols-2 gap-2.5">
      {#each shown as asset (asset.id)}
        <div class="group flex flex-col gap-1.5">
          <div class="relative aspect-video overflow-hidden rounded-lg bg-slate-950 ring-1 ring-white/10">
            {#if asset.type === 'video'}
              <!-- svelte-ignore a11y_media_has_caption -->
              <video
                src={`${asset.url}#t=0.1`}
                preload="metadata"
                muted
                class="h-full w-full object-cover"
              ></video>
              <span class="absolute right-1 bottom-1 rounded bg-black/70 px-1 text-[10px] font-medium">
                {clock(asset.duration)}
              </span>
            {:else}
              <img src={asset.url} alt="" class="h-full w-full object-cover" loading="lazy" />
            {/if}
            <div
              class="absolute inset-0 flex items-center justify-center gap-1 bg-black/55 opacity-0 transition group-focus-within:opacity-100 group-hover:opacity-100"
            >
              <button
                class="rounded-md bg-[image:var(--sun-gradient)] px-2 py-1 text-[11px] font-semibold text-sun-950 hover:brightness-110 disabled:opacity-40"
                disabled={!hasScene}
                title={hasScene ? t('editor.media.useTip') : t('editor.selectSceneFirst')}
                onclick={() => onuse(asset)}>{t('editor.media.use')}</button
              >
              <button
                class="rounded-md bg-slate-800 px-2 py-1 text-[11px] font-medium hover:bg-slate-700"
                title={t('editor.media.addSceneTip')}
                onclick={() => onaddscene(asset)}>{t('editor.media.addScene')}</button
              >
            </div>
          </div>
          <p class="truncate text-[11px] text-slate-400" title={asset.original_filename ?? ''}>
            {asset.original_filename}
          </p>
        </div>
      {/each}
    </div>
  {/if}
</div>
