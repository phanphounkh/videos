<script lang="ts">
  import SceneCard from '$lib/components/editor/SceneCard.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import { t, tn } from '$lib/i18n/index.svelte';
  import type { Scene } from '$lib/types/api';

  let {
    scenes,
    selectedId,
    onselect,
    onreorder,
    onadd
  }: {
    scenes: Scene[];
    selectedId: string | null;
    onselect: (id: string) => void;
    onreorder: (ids: string[]) => void;
    onadd: () => void;
  } = $props();

  function move(id: string, delta: number) {
    const ids = scenes.map((s) => s.id);
    const index = ids.indexOf(id);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= ids.length) return;
    [ids[index], ids[target]] = [ids[target], ids[index]];
    onreorder(ids);
  }
</script>

<div class="flex flex-col gap-3">
  <div class="flex items-center justify-between">
    <h3 class="section-title">{tn('editor.scenes.count', scenes.length)}</h3>
    <Button variant="secondary" size="sm" icon="plus" onclick={onadd}>{t('editor.scenes.add')}</Button>
  </div>

  <div class="flex flex-col gap-2">
    {#each scenes as scene (scene.id)}
      <SceneCard
        {scene}
        selected={scene.id === selectedId}
        {onselect}
        onmoveup={(id) => move(id, -1)}
        onmovedown={(id) => move(id, 1)}
      />
    {/each}
    {#if !scenes.length}
      <p class="rounded-xl border border-dashed border-slate-800 p-5 text-center text-sm text-slate-500">
        {t('editor.scenes.empty')}
      </p>
    {/if}
  </div>
</div>
