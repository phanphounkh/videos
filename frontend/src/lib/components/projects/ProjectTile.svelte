<script lang="ts">
  /**
   * One project, as a card or a table row: a tick box (visible on hover, always once
   * something is selected), the star, a "⋯" menu, and a click that opens the editor.
   */
  import { ago, mmss } from '$lib/format';
  import { t, tn } from '$lib/i18n/index.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Menu, { type MenuItem } from '$lib/components/ui/Menu.svelte';
  import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
  import type { Project } from '$lib/types/api';

  export type TileAction = 'rename' | 'duplicate' | 'move' | 'trash' | 'restore' | 'delete';

  let {
    project,
    selected = false,
    selecting = false,
    trashed = false,
    layout = 'grid',
    onselect,
    onstar,
    onaction
  }: {
    project: Project;
    selected?: boolean;
    /** Something is selected somewhere: show every tick box. */
    selecting?: boolean;
    trashed?: boolean;
    layout?: 'grid' | 'list';
    onselect: (id: string) => void;
    onstar: (project: Project) => void;
    onaction: (action: TileAction, project: Project) => void;
  } = $props();

  const items = $derived<MenuItem[]>(
    trashed
      ? [
          { label: t('common.restore'), icon: 'redo', onclick: () => onaction('restore', project) },
          { label: t('projects.deleteForever'), icon: 'trash', danger: true, separator: true, onclick: () => onaction('delete', project) }
        ]
      : [
          { label: t('common.open'), icon: 'film', onclick: () => (location.href = `/projects/${project.id}`) },
          { label: t('common.rename'), icon: 'pencil', onclick: () => onaction('rename', project) },
          { label: t('common.duplicate'), icon: 'copy', onclick: () => onaction('duplicate', project) },
          { label: t('projects.tile.moveToFolder'), icon: 'folder', onclick: () => onaction('move', project) },
          { label: t('projects.tile.moveToTrash'), icon: 'trash', danger: true, separator: true, onclick: () => onaction('trash', project) }
        ]
  );
  const href = $derived(trashed ? undefined : `/projects/${project.id}`);
  const when = $derived(
    trashed && project.deleted_at ? t('projects.tile.deleted', { when: ago(project.deleted_at) }) : t('projects.tile.updated', { when: ago(project.updated_at) })
  );
</script>

{#snippet tick()}
  <button
    type="button"
    role="checkbox"
    aria-checked={selected}
    aria-label={t('projects.tile.select', { title: project.title })}
    class="grid h-6 w-6 place-items-center rounded-md border bg-slate-950/80 backdrop-blur transition {selected
      ? 'border-sun-400 bg-sun-400 text-sun-950'
      : 'border-slate-500 text-transparent hover:border-slate-300'}"
    onclick={(e) => {
      // Inside a link: ticking must not open the project.
      e.preventDefault();
      e.stopPropagation();
      onselect(project.id);
    }}
  >
    <Icon name="check" size={14} />
  </button>
{/snippet}

{#snippet star()}
  <button
    type="button"
    class="grid h-8 w-8 shrink-0 place-items-center rounded-lg transition hover:bg-slate-800 {project.starred ? 'text-sun-400' : 'text-slate-500 hover:text-slate-200'}"
    aria-label={project.starred ? t('projects.tile.unstar') : t('projects.tile.star')}
    aria-pressed={project.starred}
    onclick={(e) => {
      e.preventDefault();
      e.stopPropagation();
      onstar(project);
    }}
  >
    <svg width="17" height="17" viewBox="0 0 24 24" fill={project.starred ? 'currentColor' : 'none'} stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M11.525 2.295a.53.53 0 0 1 .95 0l2.31 4.679a2.123 2.123 0 0 0 1.595 1.16l5.166.756a.53.53 0 0 1 .294.904l-3.736 3.638a2.123 2.123 0 0 0-.611 1.878l.882 5.14a.53.53 0 0 1-.771.56l-4.618-2.428a2.122 2.122 0 0 0-1.973 0L6.396 21.01a.53.53 0 0 1-.77-.56l.881-5.139a2.122 2.122 0 0 0-.611-1.879L2.16 9.795a.53.53 0 0 1 .294-.906l5.165-.755a2.122 2.122 0 0 0 1.597-1.16z" />
    </svg>
  </button>
{/snippet}

{#snippet picture()}
  {#if project.thumbnail_url}
    <img src={project.thumbnail_url} alt="" loading="lazy" class="h-full w-full object-contain transition duration-300 group-hover:scale-[1.02]" />
  {:else}
    <div class="grid h-full w-full place-items-center bg-gradient-to-br from-slate-900 to-slate-950 text-slate-600"><Icon name="film" size={26} /></div>
  {/if}
{/snippet}

{#if layout === 'grid'}
  <article
    class="group relative flex flex-col overflow-hidden rounded-2xl border bg-slate-900/50 transition {selected
      ? 'border-sun-400 shadow-glow'
      : 'border-slate-800 hover:border-slate-600'}"
  >
    <svelte:element this={href ? 'a' : 'div'} {href} class="relative block aspect-video overflow-hidden bg-slate-950" aria-label={trashed ? undefined : t('projects.tile.openProject', { title: project.title })}>
      {@render picture()}
      <div class="absolute top-2.5 left-2.5 transition {selected || selecting ? 'opacity-100' : 'opacity-0 group-focus-within:opacity-100 group-hover:opacity-100'}">
        {@render tick()}
      </div>
      <span class="absolute right-2.5 bottom-2.5 rounded-md bg-slate-950/80 px-1.5 py-0.5 font-mono text-xs text-slate-100">{mmss(project.duration)}</span>
    </svelte:element>
    <Menu {items} class="absolute top-2.5 right-2.5 transition {selecting ? 'opacity-0 group-hover:opacity-100' : 'opacity-0 group-focus-within:opacity-100 group-hover:opacity-100'}" />
    <div class="flex flex-col gap-1.5 p-3.5">
      <div class="flex items-start justify-between gap-2">
        <svelte:element this={href ? 'a' : 'p'} {href} class="line-clamp-2 text-[15px] leading-snug font-semibold text-slate-50 {href ? 'hover:text-sun-300' : ''}" style="line-height:1.5">{project.title}</svelte:element>
        {#if !trashed}{@render star()}{/if}
      </div>
      <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500">
        <span class="rounded-md bg-slate-800 px-1.5 py-0.5 text-slate-300">{project.aspect_ratio}</span>
        <span>{when}</span>
        {#if project.status !== 'ready'}<StatusBadge status={project.status} />{/if}
      </p>
    </div>
  </article>
{:else}
  <div class="group relative flex items-center gap-3 rounded-xl border px-3 py-2 transition {selected ? 'border-sun-400 bg-sun-400/5' : 'border-transparent hover:border-slate-800 hover:bg-slate-900/60'}">
    {@render tick()}
    <svelte:element this={href ? 'a' : 'div'} {href} class="h-12 w-20 shrink-0 overflow-hidden rounded-lg bg-slate-950">{@render picture()}</svelte:element>
    <svelte:element this={href ? 'a' : 'p'} {href} class="min-w-0 flex-1 truncate text-sm font-medium text-slate-100 {href ? 'hover:text-sun-300' : ''}">{project.title}</svelte:element>
    <span class="hidden w-24 sm:block"><StatusBadge status={project.status} /></span>
    <span class="hidden w-14 rounded-md bg-slate-800 px-1.5 py-0.5 text-center text-xs text-slate-300 md:block">{project.aspect_ratio}</span>
    <span class="hidden w-14 text-right font-mono text-xs text-slate-400 md:block">{mmss(project.duration)}</span>
    <span class="hidden w-32 text-right text-xs text-slate-500 lg:block">{when}</span>
    {#if !trashed}{@render star()}{/if}
    <Menu {items} />
  </div>
{/if}
