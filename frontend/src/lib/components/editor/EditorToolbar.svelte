<script lang="ts">
  /** The strip above the timeline. Shortcuts themselves are handled by VideoEditor. */
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';

  let {
    canSplit,
    hasSelection,
    onsplit,
    ondelete,
    onduplicate,
    onaddtext,
    onaddsticker,
    onupload,
    onzoomin,
    onzoomout,
    onfit
  }: {
    canSplit: boolean;
    hasSelection: boolean;
    onsplit: () => void;
    ondelete: () => void;
    onduplicate: () => void;
    onaddtext: () => void;
    onaddsticker: () => void;
    onupload: () => void;
    onzoomin: () => void;
    onzoomout: () => void;
    onfit: () => void;
  } = $props();
</script>

{#snippet tool(icon: IconName, label: string, tip: string, click: () => void, disabled = false)}
  <button
    class="inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium text-slate-300 transition hover:bg-slate-800 hover:text-slate-50 disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:bg-transparent"
    title={tip}
    aria-label={label}
    {disabled}
    onclick={click}
  >
    <Icon name={icon} size={15} />
    <span class="hidden xl:inline">{label}</span>
  </button>
{/snippet}

{#snippet divider()}
  <span class="mx-1 h-5 w-px bg-slate-800"></span>
{/snippet}

<div
  class="flex h-11 shrink-0 items-center gap-0.5 border-y border-slate-800 bg-slate-900 px-2"
  role="toolbar"
  aria-label="Editing tools"
>
  {@render tool('scissors', 'Split', 'Split the scene at the playhead (S)', onsplit, !canSplit)}
  {@render tool('copy', 'Duplicate', 'Duplicate (Ctrl+D)', onduplicate, !hasSelection)}
  {@render tool('trash', 'Delete', 'Delete (Delete)', ondelete, !hasSelection)}
  {@render divider()}
  {@render tool('type', 'Text', 'Add text at the playhead', onaddtext)}
  {@render tool('smile', 'Sticker', 'Add a sticker at the playhead', onaddsticker)}
  {@render tool('upload', 'Media', "Replace the selected scene's picture or clip", onupload)}

  <span class="flex-1"></span>

  {@render tool('zoomOut', 'Zoom out', 'Zoom out (-)', onzoomout)}
  {@render tool('fit', 'Fit', 'Fit the whole video', onfit)}
  {@render tool('zoomIn', 'Zoom in', 'Zoom in (+)', onzoomin)}
</div>
