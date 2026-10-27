<script lang="ts">
  /** Add styled text, and jump to any text already on the video. */
  import Icon from '$lib/components/ui/Icon.svelte';
  import { layersOf } from '$lib/editor/layers';
  import { t } from '$lib/i18n/index.svelte';
  import type { Layer, Scene } from '$lib/types/api';

  let {
    scenes,
    selectedLayerId,
    onadd,
    onselect
  }: {
    scenes: Scene[];
    selectedLayerId: string | null;
    onadd: (patch: Partial<Layer>) => void;
    onselect: (sceneId: string, layerId: string) => void;
  } = $props();

  const presets = [
    { label: 'editor.text.heading', cls: 'text-2xl font-extrabold', patch: { font_size: 12, weight: 800 } },
    { label: 'editor.text.subheading', cls: 'text-lg font-bold', patch: { font_size: 8, weight: 700 } },
    { label: 'editor.text.body', cls: 'text-sm font-medium', patch: { font_size: 5, weight: 500 } }
  ];

  const texts = $derived(
    [...scenes]
      .sort((a, b) => a.scene_number - b.scene_number)
      .flatMap((scene) =>
        layersOf(scene)
          .filter((layer) => layer.type === 'text')
          .map((layer) => ({ scene, layer }))
      )
  );
</script>

<div class="flex flex-col gap-4">
  <div class="flex flex-col gap-2">
    {#each presets as preset (preset.label)}
      <button
        class="flex h-14 items-center rounded-xl border border-slate-800 bg-slate-900/60 px-4 text-left text-slate-100 transition hover:border-sun-400/50 hover:bg-slate-900 {preset.cls}"
        onclick={() => onadd(preset.patch)}
      >
        {t(preset.label)}
      </button>
    {/each}
  </div>

  <section class="flex flex-col gap-2">
    <h3 class="section-title">{t('editor.text.onVideo')}</h3>
    {#if !texts.length}
      <p class="rounded-lg border border-dashed border-slate-800 p-3 text-sm text-slate-500">
        {t('editor.text.empty')}
      </p>
    {:else}
      <ul class="flex flex-col gap-1">
        {#each texts as { scene, layer } (layer.id)}
          <li>
            <button
              class="flex w-full items-center gap-2 rounded-lg border px-3 py-1.5 text-left text-sm transition {layer.id ===
              selectedLayerId
                ? 'border-sun-400/60 bg-sun-400/10 text-slate-50'
                : 'border-slate-800 text-slate-300 hover:border-slate-600'}"
              onclick={() => onselect(scene.id, layer.id)}
            >
              <Icon name="type" size={13} class="shrink-0 text-slate-500" />
              <span class="min-w-0 flex-1 truncate">{layer.text}</span>
              <span class="shrink-0 text-xs text-slate-500">#{scene.scene_number}</span>
            </button>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</div>
