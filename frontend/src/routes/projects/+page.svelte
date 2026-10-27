<script lang="ts">
  /**
   * Projects, the way Canva and Drive lay it out: tabs for All, Recent and Starred, folder
   * cards, a grid or a list of projects with tick boxes, and a bar of bulk actions that
   * appears once something is selected. The Trash is the same page with `?view=trash`.
   */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import ProjectTile, { type TileAction } from '$lib/components/projects/ProjectTile.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Menu from '$lib/components/ui/Menu.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import { t, tn } from '$lib/i18n/index.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import type { BulkAction, Folder, Project, ProjectView } from '$lib/types/api';

  const TABS: ProjectView[] = ['all', 'recent', 'starred'];
  const LAYOUT_KEY = 'sorya.projects.layout';

  const view = $derived((page.url.searchParams.get('view') as ProjectView | null) ?? 'all');
  const folderId = $derived(page.url.searchParams.get('folder'));
  const q = $derived(page.url.searchParams.get('q') ?? '');
  const sort = $derived((page.url.searchParams.get('sort') as 'recent' | 'title' | 'created' | null) ?? 'recent');
  const trash = $derived(view === 'trash');

  let projects = $state<Project[]>([]);
  let total = $state(0);
  let folders = $state<Folder[]>([]);
  let loading = $state(true);
  let error = $state<unknown>(null);
  let selected = $state(new Set<string>());
  let layout = $state<'grid' | 'list'>('grid');
  let search = $state('');
  let notice = $state('');

  // dialogs
  type Dialog =
    | { kind: 'newFolder' }
    | { kind: 'renameFolder'; folder: Folder }
    | { kind: 'deleteFolder'; folder: Folder }
    | { kind: 'renameProject'; project: Project }
    | { kind: 'move'; ids: string[] }
    | { kind: 'deleteForever'; ids: string[] }
    | { kind: 'emptyTrash' };
  let dialog = $state<Dialog | null>(null);
  let text = $state('');
  let target = $state<string>('');

  $effect(() => {
    try {
      layout = localStorage.getItem(LAYOUT_KEY) === 'list' ? 'list' : 'grid';
    } catch {
      // grid
    }
  });
  const setLayout = (next: 'grid' | 'list') => {
    layout = next;
    try {
      localStorage.setItem(LAYOUT_KEY, next);
    } catch {
      // not remembered
    }
  };

  function go(params: { view?: ProjectView; folder?: string | null; q?: string; sort?: string }) {
    const next = new URLSearchParams();
    const v = params.view ?? view;
    const f = params.folder === undefined ? folderId : params.folder;
    const query = params.q === undefined ? q : params.q;
    const s = params.sort ?? sort;
    if (v !== 'all') next.set('view', v);
    if (f) next.set('folder', f);
    if (query) next.set('q', query);
    if (s !== 'recent') next.set('sort', s);
    void goto(`/projects${next.size ? `?${next}` : ''}`, { replaceState: true, keepFocus: true, noScroll: true });
  }

  let generation = 0;
  let lastScope = '';
  async function load() {
    const mine = ++generation;
    loading = true;
    // Opening another folder or tab must not show the previous one's projects meanwhile.
    const scope = `${view}|${folderId ?? ''}`;
    if (scope !== lastScope) {
      projects = [];
      selected = new Set();
      lastScope = scope;
    }
    try {
      const [list, folderList] = await Promise.all([
        api.listProjects({ view, folder: folderId ?? undefined, q, sort }),
        api.listFolders()
      ]);
      if (mine !== generation) return;
      projects = list.items;
      total = list.total;
      folders = folderList;
      selected = new Set([...selected].filter((id) => list.items.some((p) => p.id === id)));
      error = null;
    } catch (e) {
      if (mine === generation) error = e;
    } finally {
      if (mine === generation) loading = false;
    }
  }

  $effect(() => {
    if (!auth.ready) return;
    if (!auth.user) {
      void goto('/login', { replaceState: true });
      return;
    }
    void page.url.search;
    void load();
  });
  $effect(() => {
    search = q;
  });

  const showFolders = $derived(view === 'all' && !folderId && !q && !trash);
  const currentFolder = $derived(folders.find((f) => f.id === folderId) ?? null);
  const selecting = $derived(selected.size > 0);
  const selectedIds = $derived([...selected]);
  const allSelected = $derived(projects.length > 0 && projects.every((p) => selected.has(p.id)));

  function toggle(id: string) {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    selected = next;
  }

  async function run(action: BulkAction, ids: string[], message: string, folder?: string | null) {
    try {
      await api.bulkProjects(ids, action, folder);
      notice = message;
      selected = new Set();
      await load();
    } catch (e) {
      error = e;
    }
  }

  async function star(p: Project) {
    p.starred = !p.starred;
    try {
      await api.updateProject(p.id, { starred: p.starred });
      if (view === 'starred' && !p.starred) await load();
    } catch (e) {
      p.starred = !p.starred;
      error = e;
    }
  }

  function tileAction(action: TileAction, p: Project) {
    if (action === 'rename') {
      text = p.title;
      dialog = { kind: 'renameProject', project: p };
    } else if (action === 'move') {
      target = p.folder_id ?? '';
      dialog = { kind: 'move', ids: [p.id] };
    } else if (action === 'duplicate') void run('duplicate', [p.id], t('projects.notice.duplicated'));
    else if (action === 'trash') void run('trash', [p.id], t('projects.notice.trashed'));
    else if (action === 'restore') void run('restore', [p.id], t('projects.notice.restored'));
    else dialog = { kind: 'deleteForever', ids: [p.id] };
  }

  async function submitDialog() {
    const d = dialog;
    if (!d) return;
    try {
      if (d.kind === 'newFolder') {
        const folder = await api.createFolder(text.trim());
        notice = t('projects.notice.folderCreated', { name: folder.name });
      } else if (d.kind === 'renameFolder') {
        await api.renameFolder(d.folder.id, text.trim());
      } else if (d.kind === 'deleteFolder') {
        await api.deleteFolder(d.folder.id);
        notice = t('projects.notice.folderDeleted');
        if (folderId === d.folder.id) go({ folder: null });
      } else if (d.kind === 'renameProject') {
        await api.updateProject(d.project.id, { title: text.trim() });
      } else if (d.kind === 'move') {
        await api.bulkProjects(d.ids, 'move', target || null);
        notice = t('projects.notice.moved');
        selected = new Set();
      } else if (d.kind === 'deleteForever') {
        await api.bulkProjects(d.ids, 'delete');
        notice = t('projects.notice.deleted');
        selected = new Set();
      } else if (d.kind === 'emptyTrash') {
        await api.emptyTrash();
        notice = t('projects.notice.trashEmptied');
      }
      dialog = null;
      await load();
    } catch (e) {
      dialog = null;
      error = e;
    }
  }

  const needsText = $derived(dialog?.kind === 'newFolder' || dialog?.kind === 'renameFolder' || dialog?.kind === 'renameProject');
  const input =
    'h-10 w-full rounded-lg border border-slate-700 bg-slate-950 px-3 text-sm text-slate-100 focus:border-sun-400 focus:outline-none';
</script>

<svelte:head><title>{trash ? t('projects.trash') : t('projects.title')} · Sorya</title></svelte:head>

<main class="mx-auto flex max-w-[120rem] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-10">
  <!-- title row -->
  <div class="flex flex-wrap items-center justify-between gap-3">
    <div class="flex min-w-0 items-center gap-3">
      {#if currentFolder}
        <a href="/projects" class="text-sm text-slate-400 hover:text-slate-100">{t('projects.title')}</a>
        <span class="text-slate-600">/</span>
      {/if}
      <h1 class="truncate text-[30px] leading-tight font-bold tracking-tight text-slate-50">
        {trash ? t('projects.trash') : (currentFolder?.name ?? t('projects.title'))}
      </h1>
      <span class="rounded-full bg-slate-800 px-2.5 py-0.5 text-sm font-medium text-slate-300">{total}</span>
      {#if currentFolder}
        <Menu
          label={t('projects.folderActions')}
          align="left"
          items={[
            { label: t('projects.renameFolder'), icon: 'pencil', onclick: () => ((text = currentFolder.name), (dialog = { kind: 'renameFolder', folder: currentFolder })) },
            { label: t('projects.deleteFolder'), icon: 'trash', danger: true, onclick: () => (dialog = { kind: 'deleteFolder', folder: currentFolder }) }
          ]}
        />
      {/if}
    </div>
    {#if trash}
      <Button variant="danger" icon="trash" disabled={!projects.length} onclick={() => (dialog = { kind: 'emptyTrash' })}>{t('projects.emptyTrash')}</Button>
    {:else}
      <div class="flex items-center gap-2">
        <Button variant="secondary" icon="folderPlus" onclick={() => ((text = ''), (dialog = { kind: 'newFolder' }))}>{t('projects.newFolder')}</Button>
        <a href="/create"><Button icon="plus">{t('projects.newProject')}</Button></a>
      </div>
    {/if}
  </div>

  {#if trash}
    <p class="rounded-xl border border-slate-800 bg-slate-900/50 px-4 py-3 text-sm text-slate-400">
      {t('projects.trashNote')}
    </p>
  {/if}

  <ErrorBanner {error} />
  {#if notice}
    <p class="flex items-center justify-between rounded-xl border border-emerald-500/25 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-200" role="status">
      {notice}
      <button type="button" class="text-emerald-300 hover:text-emerald-100" aria-label={t('common.dismiss')} onclick={() => (notice = '')}><Icon name="x" size={14} /></button>
    </p>
  {/if}

  <!-- tabs + tools -->
  {#if !trash}
    <div class="flex flex-wrap items-end justify-between gap-x-6 gap-y-3 border-b border-slate-800">
      <nav class="flex gap-1" aria-label={t('projects.views')}>
        {#each TABS as tab (tab)}
          <button
            type="button"
            aria-current={view === tab ? 'page' : undefined}
            class="-mb-px border-b-2 px-3 py-2.5 text-sm font-medium transition {view === tab ? 'border-sun-400 text-sun-200' : 'border-transparent text-slate-400 hover:text-slate-100'}"
            onclick={() => go({ view: tab })}>{t(`projects.tab.${tab}`)}</button
          >
        {/each}
      </nav>
      <div class="flex flex-wrap items-center gap-2 pb-2">
        <form
          class="relative"
          onsubmit={(e) => {
            e.preventDefault();
            go({ q: search.trim() });
          }}
        >
          <Icon name="search" size={15} class="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500" />
          <input type="search" bind:value={search} data-private placeholder={t('projects.searchPlaceholder')} aria-label={t('projects.search')} class="h-9 w-56 rounded-lg border border-slate-700 bg-slate-900 pr-3 pl-9 text-sm text-slate-100 placeholder:text-slate-500 focus:border-sun-400 focus:outline-none" />
        </form>
        <select value={sort} aria-label={t('projects.sort')} class="h-9 rounded-lg border border-slate-700 bg-slate-900 py-0 pr-8 pl-3 text-sm text-slate-200 focus:border-sun-400 focus:outline-none" onchange={(e) => go({ sort: e.currentTarget.value })}>
          <option value="recent">{t('projects.sort.recent')}</option>
          <option value="created">{t('projects.sort.created')}</option>
          <option value="title">{t('projects.sort.title')}</option>
        </select>
        <div class="inline-flex rounded-lg border border-slate-700 bg-slate-900 p-0.5" role="group" aria-label={t('projects.layout')}>
          {#each [['grid', 'grid', 'projects.gridView'], ['list', 'list', 'projects.listView']] as [value, icon, label] (value)}
            <button type="button" class="grid h-8 w-8 place-items-center rounded-md transition {layout === value ? 'bg-slate-700 text-slate-50' : 'text-slate-400 hover:text-slate-200'}" aria-pressed={layout === value} aria-label={t(label)} title={t(label)} onclick={() => setLayout(value as 'grid' | 'list')}>
              <Icon name={icon as 'grid' | 'list'} size={16} />
            </button>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  <!-- folders -->
  {#if showFolders && folders.length}
    <section aria-label={t('projects.folders')}>
      <ul class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
        {#each folders as folder (folder.id)}
          <li class="group relative">
            <a href="/projects?folder={folder.id}" class="flex items-center gap-3 rounded-2xl border border-slate-800 bg-slate-900/50 p-3 transition hover:border-slate-600">
              <span class="grid h-12 w-12 shrink-0 place-items-center rounded-xl bg-slate-800 text-sun-300"><Icon name="folder" size={22} /></span>
              {#if folder.cover_url}<img src={folder.cover_url} alt="" class="h-12 w-16 shrink-0 rounded-lg object-cover" />{/if}
              <span class="min-w-0 flex-1">
                <span class="block truncate font-semibold text-slate-50">{folder.name}</span>
                <span class="block text-xs text-slate-500">{tn('projects.folderCount', folder.project_count)}</span>
              </span>
            </a>
            <Menu
              class="absolute top-1/2 right-3 -translate-y-1/2 opacity-0 transition group-focus-within:opacity-100 group-hover:opacity-100"
              label={t('projects.folderActions')}
              items={[
                { label: t('common.rename'), icon: 'pencil', onclick: () => ((text = folder.name), (dialog = { kind: 'renameFolder', folder })) },
                { label: t('projects.deleteFolder'), icon: 'trash', danger: true, onclick: () => (dialog = { kind: 'deleteFolder', folder }) }
              ]}
            />
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <!-- projects -->
  {#if loading && !projects.length}
    <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5" aria-busy="true">
      {#each [0, 1, 2] as n (n)}
        <div class="animate-pulse overflow-hidden rounded-2xl border border-slate-800"><div class="aspect-video bg-slate-800/60"></div><div class="space-y-3 p-4"><div class="h-4 w-3/4 rounded bg-slate-800"></div><div class="h-3 w-1/2 rounded bg-slate-800/70"></div></div></div>
      {/each}
    </div>
  {:else if !projects.length && !error}
    <div class="flex flex-col items-center gap-3 rounded-2xl border border-dashed border-slate-700 px-6 py-16 text-center">
      <span class="grid h-14 w-14 place-items-center rounded-2xl bg-slate-800 text-slate-400"><Icon name={trash ? 'trash' : view === 'starred' ? 'star' : 'film'} size={26} /></span>
      <h2 class="text-lg font-semibold text-slate-50">
        {trash ? t('projects.empty.trash') : q ? t('projects.empty.search') : view === 'starred' ? t('projects.empty.starred') : currentFolder ? t('projects.empty.folder') : t('projects.empty.none')}
      </h2>
      <p class="max-w-sm text-sm text-slate-400">
        {trash ? t('projects.emptyBody.trash') : q ? t('projects.emptyBody.search', { q }) : view === 'starred' ? t('projects.emptyBody.starred') : t('projects.emptyBody.none')}
      </p>
      {#if !trash && !q && view !== 'starred'}<a href="/create"><Button icon="plus">{t('projects.newProject')}</Button></a>{/if}
      {#if q}<Button variant="secondary" onclick={() => go({ q: '' })}>{t('projects.clearSearch')}</Button>{/if}
    </div>
  {:else}
    <div class={layout === 'grid' ? 'grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5' : 'flex flex-col gap-1'}>
      {#each projects as project (project.id)}
        <ProjectTile {project} {layout} {selecting} trashed={trash} selected={selected.has(project.id)} onselect={toggle} onstar={star} onaction={tileAction} />
      {/each}
    </div>
  {/if}
</main>

<!-- bulk bar -->
{#if selecting}
  <div class="sticky bottom-4 z-40 flex justify-center px-4">
    <div class="flex max-w-full flex-wrap items-center gap-2 rounded-2xl border border-slate-700 bg-slate-900/95 px-4 py-3 shadow-2xl shadow-black/60 backdrop-blur" role="toolbar" aria-label={t('projects.bulkLabel')}>
      <label class="flex items-center gap-2 pr-2 text-sm font-medium text-slate-100">
        <input type="checkbox" checked={allSelected} aria-label={t('projects.selectAll')} onchange={() => (selected = allSelected ? new Set() : new Set(projects.map((p) => p.id)))} />
        {t('projects.selected', { n: selected.size })}
      </label>
      <span class="mx-1 h-6 w-px bg-slate-700"></span>
      {#if trash}
        <Button variant="secondary" size="sm" icon="redo" onclick={() => run('restore', selectedIds, t('projects.notice.restored'))}>{t('common.restore')}</Button>
        <Button variant="danger" size="sm" icon="trash" onclick={() => (dialog = { kind: 'deleteForever', ids: selectedIds })}>{t('projects.deleteForever')}</Button>
      {:else}
        <Button variant="secondary" size="sm" icon="folder" onclick={() => ((target = ''), (dialog = { kind: 'move', ids: selectedIds }))}>{t('projects.move')}</Button>
        <Button variant="secondary" size="sm" icon="copy" onclick={() => run('duplicate', selectedIds, t('projects.notice.duplicated'))}>{t('common.duplicate')}</Button>
        <Button variant="secondary" size="sm" onclick={() => run('star', selectedIds, t('projects.notice.starred'))}>{t('projects.star')}</Button>
        <Button variant="danger" size="sm" icon="trash" onclick={() => run('trash', selectedIds, t('projects.notice.trashed'))}>{t('projects.trashAction')}</Button>
      {/if}
      <Button variant="ghost" size="sm" onclick={() => (selected = new Set())}>{t('projects.cancelSelection')}</Button>
    </div>
  </div>
{/if}

<!-- dialogs -->
{#if dialog}
  <Modal
    onclose={() => (dialog = null)}
    title={t(`projects.dialog.${dialog.kind}`)}
  >
    {#if needsText}
      <form id="dialog-form" onsubmit={(e) => (e.preventDefault(), text.trim() && submitDialog())}>
        <!-- svelte-ignore a11y_autofocus -->
        <input class={input} bind:value={text} maxlength={dialog.kind === 'renameProject' ? 300 : 120} placeholder={dialog.kind === 'newFolder' ? t('projects.dialog.folderPlaceholder') : ''} aria-label={t('projects.dialog.name')} autofocus data-private />
      </form>
    {:else if dialog.kind === 'move'}
      <label class="flex flex-col gap-1.5 text-sm text-slate-300">
        {t('projects.dialog.destination')}
        <select class={input} bind:value={target}>
          <option value="">{t('projects.dialog.noFolder')}</option>
          {#each folders as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
        </select>
      </label>
    {:else if dialog.kind === 'deleteFolder'}
      {tn('projects.dialog.deleteFolderBody', dialog.folder.project_count, { name: dialog.folder.name })}
    {:else if dialog.kind === 'emptyTrash'}
      {t('projects.dialog.emptyTrashBody')}
    {:else}
      {tn('projects.dialog.deleteForeverBody', dialog.kind === 'deleteForever' ? dialog.ids.length : 1)}
    {/if}
    {#snippet actions()}
      <Button variant="ghost" onclick={() => (dialog = null)}>{t('common.cancel')}</Button>
      {#if dialog && (dialog.kind === 'deleteFolder' || dialog.kind === 'deleteForever' || dialog.kind === 'emptyTrash')}
        <Button variant="danger" onclick={submitDialog}>{t('common.delete')}</Button>
      {:else}
        <Button disabled={needsText && !text.trim()} onclick={submitDialog}>{dialog?.kind === 'move' ? t('projects.move') : dialog?.kind === 'newFolder' ? t('projects.dialog.createFolder') : t('common.save')}</Button>
      {/if}
    {/snippet}
  </Modal>
{/if}
