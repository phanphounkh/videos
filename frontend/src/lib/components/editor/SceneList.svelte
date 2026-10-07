<script lang="ts">
  import Button from '$lib/components/ui/Button.svelte';
  import SceneCard from '$lib/components/editor/SceneCard.svelte';
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

<aside class="flex w-full flex-col gap-2 lg:w-72">
  <div class="flex items-center justify-between">
    <h3 class="text-xs font-semibold tracking-wide text-slate-400 uppercase">
      Scenes ({scenes.length})
    </h3>
    <Button variant="ghost" onclick={onadd}>+ Add</Button>
  </div>

  <div class="flex max-h-[60vh] flex-col gap-2 overflow-y-auto pr-1">
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
      <p class="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-500">
        No scenes yet. Generate a video or add a scene manually.
      </p>
    {/if}
  </div>
</aside>
