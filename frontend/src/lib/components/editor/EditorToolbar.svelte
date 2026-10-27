<script lang="ts">
  /** The strip above the timeline. Shortcuts themselves are handled by VideoEditor. */
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import { t } from '$lib/i18n/index.svelte';

  let {
    canSplit,
    hasSelection,
    pps,
    onsplit,
    ondelete,
    onduplicate,
    onzoom,
    onzoomin,
    onzoomout,
    onfit
  }: {
    canSplit: boolean;
    hasSelection: boolean;
    /** Pixels per second in use, shown on the zoom slider. */
    pps: number;
    onsplit: () => void;
    ondelete: () => void;
    onduplicate: () => void;
    onzoom: (pps: number) => void;
    onzoomin: () => void;
    onzoomout: () => void;
    onfit: () => void;
  } = $props();

  // The slider is logarithmic so each step feels like the same amount of zoom.
  const LOW = Math.log(2);
  const HIGH = Math.log(600);
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

<div
  class="flex h-11 shrink-0 items-center gap-0.5 border-y border-slate-800 bg-slate-900 px-2"
  role="toolbar"
  aria-label={t('editor.tl.tools')}
>
  <span
    class="grid h-8 w-8 place-items-center rounded-md bg-slate-800 text-sun-300"
    title={t('editor.tl.selectTip')}
  >
    <Icon name="pointer" size={15} />
  </span>
  <span class="mx-1 h-5 w-px bg-slate-800"></span>
  {@render tool('scissors', t('editor.tl.split'), t('editor.tl.splitTip'), onsplit, !canSplit)}
  {@render tool('trash', t('editor.tl.delete'), t('editor.tl.deleteTip'), ondelete, !hasSelection)}
  {@render tool('copy', t('editor.tl.duplicate'), t('editor.tl.duplicateTip'), onduplicate, !hasSelection)}

  <span class="flex-1"></span>

  <button
    class="grid h-8 w-8 place-items-center rounded-md text-slate-300 transition hover:bg-slate-800 hover:text-slate-50"
    title={t('editor.tl.zoomOutTip')}
    aria-label={t('editor.tl.zoomOut')}
    onclick={onzoomout}><Icon name="zoomOut" size={15} /></button
  >
  <input
    type="range"
    min={LOW}
    max={HIGH}
    step="0.01"
    value={Math.log(Math.max(2, Math.min(600, pps)))}
    oninput={(e) => onzoom(Math.exp(Number(e.currentTarget.value)))}
    class="mx-1 h-1 w-28 cursor-pointer accent-sun-500"
    aria-label={t('editor.tl.zoom')}
  />
  <button
    class="grid h-8 w-8 place-items-center rounded-md text-slate-300 transition hover:bg-slate-800 hover:text-slate-50"
    title={t('editor.tl.zoomInTip')}
    aria-label={t('editor.tl.zoomIn')}
    onclick={onzoomin}><Icon name="zoomIn" size={15} /></button
  >
  <button
    class="ml-1 inline-flex h-8 items-center gap-1.5 rounded-md px-2.5 text-xs font-medium text-slate-300 transition hover:bg-slate-800 hover:text-slate-50"
    title={t('editor.tl.fitTip')}
    aria-label={t('editor.tl.fit')}
    onclick={onfit}
  >
    <Icon name="fit" size={15} />
    {t('editor.tl.fit')}
  </button>
</div>
