<script lang="ts" module>
  export type Tool = 'scenes' | 'media' | 'text' | 'elements' | 'audio' | 'captions';
</script>

<script lang="ts">
  /** The narrow icon rail on the left: one tab per tool, each opening a panel beside it. */
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import { t } from '$lib/i18n/index.svelte';

  let { tool = $bindable<Tool>('scenes') }: { tool?: Tool } = $props();

  const items: { id: Tool; label: string; icon: IconName }[] = [
    { id: 'scenes', label: 'editor.tool.scenes', icon: 'film' },
    { id: 'media', label: 'editor.tool.media', icon: 'image' },
    { id: 'text', label: 'editor.tool.text', icon: 'type' },
    { id: 'elements', label: 'editor.tool.elements', icon: 'shapes' },
    { id: 'audio', label: 'editor.tool.audio', icon: 'music' },
    { id: 'captions', label: 'editor.tool.captions', icon: 'captions' }
  ];
</script>

<div
  class="flex shrink-0 gap-1 overflow-x-auto border-b border-slate-800 bg-slate-950 p-1.5 lg:w-[4.5rem] lg:flex-col lg:overflow-visible lg:border-r lg:border-b-0 lg:py-3"
  role="tablist"
  aria-orientation="vertical"
  aria-label={t('editor.tool.rail')}
>
  {#each items as item (item.id)}
    <button
      role="tab"
      aria-selected={tool === item.id}
      class="flex min-w-16 flex-1 flex-col items-center gap-1 rounded-xl px-1 py-2 text-[11px] font-medium transition lg:min-w-0 lg:flex-none {tool ===
      item.id
        ? 'bg-slate-800 text-sun-300 shadow-sm'
        : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100'}"
      onclick={() => (tool = item.id)}
    >
      <Icon name={item.icon} size={20} />
      {t(item.label)}
    </button>
  {/each}
</div>
