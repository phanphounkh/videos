<script lang="ts">
  /** A grid of stickers to drop onto the scene under the playhead. */
  import { STICKERS } from '$lib/editor/layers';
  import { t } from '$lib/i18n/index.svelte';

  let { onadd }: { onadd: (emoji: string) => void } = $props();
</script>

<div class="flex flex-col gap-3">
  <p class="text-xs text-slate-500">{t('editor.elements.hint')}</p>
  <div class="grid grid-cols-4 gap-2">
    {#each STICKERS as emoji (emoji)}
      <button
        class="grid aspect-square place-items-center rounded-xl border border-slate-800 bg-slate-900/60 text-2xl transition hover:border-sun-400/50 hover:bg-slate-900"
        aria-label={t('editor.elements.add', { emoji })}
        onclick={() => onadd(emoji)}>{emoji}</button
      >
    {/each}
  </div>
</div>
