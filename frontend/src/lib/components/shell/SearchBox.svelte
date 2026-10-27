<script lang="ts">
  /** The top-bar search: finds your projects and the templates as you type. */
  import { t, tn } from '$lib/i18n/index.svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import Icon from '$lib/components/ui/Icon.svelte';
  import type { Project, TemplateItem } from '$lib/types/api';

  let { large = false, placeholder = undefined }: { large?: boolean; placeholder?: string } = $props();

  let query = $state('');
  let open = $state(false);
  let projects = $state<Project[] | null>(null);
  let templates = $state<TemplateItem[]>([]);
  let root = $state<HTMLElement | undefined>();

  async function load() {
    if (projects !== null) return;
    projects = [];
    try {
      const [p, t] = await Promise.all([api.listProjects(), api.templates()]);
      projects = p.items;
      templates = t.templates;
    } catch {
      // Search still works as a plain "search projects" jump.
    }
  }

  const q = $derived(query.trim().toLowerCase());
  const foundProjects = $derived(
    q ? (projects ?? []).filter((p) => p.title.toLowerCase().includes(q)).slice(0, 5) : []
  );
  const foundTemplates = $derived(
    q ? templates.filter((t) => t.title.toLowerCase().includes(q)).slice(0, 3) : []
  );

  function submit(e: SubmitEvent) {
    e.preventDefault();
    open = false;
    void goto(q ? `/projects?q=${encodeURIComponent(query.trim())}` : '/projects');
  }

  $effect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => {
      if (root && !root.contains(e.target as Node)) open = false;
    };
    document.addEventListener('pointerdown', away);
    return () => document.removeEventListener('pointerdown', away);
  });
</script>

<div class="relative w-full {large ? 'max-w-4xl' : 'max-w-xl'}" bind:this={root}>
  <form onsubmit={submit} role="search">
    <Icon name="search" size={large ? 20 : 16} class="pointer-events-none absolute top-1/2 -translate-y-1/2 text-slate-500 {large ? 'left-5' : 'left-3.5'}" />
    <input
      type="search"
      bind:value={query}
      data-private
      placeholder={placeholder ?? t('search.placeholder')}
      aria-label={t('search.label')}
      class="w-full border border-slate-800 bg-slate-900 text-slate-100 placeholder:text-slate-500 focus:border-sun-400 focus:outline-none {large ? 'h-14 rounded-full pr-6 pl-14 text-base shadow-lg shadow-black/20' : 'h-10 rounded-xl pr-4 pl-10 text-sm'}"
      onfocus={() => {
        open = true;
        void load();
      }}
      oninput={() => (open = true)}
    />
  </form>

  {#if open && q}
    <div
      class="absolute z-40 mt-2 w-full overflow-hidden rounded-xl border border-slate-700 bg-slate-900 py-1 shadow-2xl shadow-black/50"
      role="listbox"
    >
      {#if foundProjects.length}
        <p class="px-3 pt-2 pb-1 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">{t('search.projects')}</p>
        {#each foundProjects as p (p.id)}
          <a
            href="/projects/{p.id}"
            role="option"
            aria-selected="false"
            class="flex items-center gap-3 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
            onclick={() => (open = false)}
          >
            <span class="grid h-8 w-12 shrink-0 place-items-center overflow-hidden rounded bg-slate-800 text-slate-500">
              {#if p.thumbnail_url}<img src={p.thumbnail_url} alt="" class="h-full w-full object-cover" />{:else}<Icon name="film" size={14} />{/if}
            </span>
            <span class="truncate">{p.title}</span>
          </a>
        {/each}
      {/if}
      {#if foundTemplates.length}
        <p class="px-3 pt-2 pb-1 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">{t('search.templates')}</p>
        {#each foundTemplates as t (t.key)}
          <a
            href="/templates"
            role="option"
            aria-selected="false"
            class="flex items-center gap-3 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800"
            onclick={() => (open = false)}
          >
            <img src={t.thumbnail_url} alt="" class="h-8 w-12 shrink-0 rounded object-cover" />
            <span class="truncate">{t.title}</span>
          </a>
        {/each}
      {/if}
      <a
        href="/projects?q={encodeURIComponent(query.trim())}"
        class="flex items-center gap-2 border-t border-slate-800 px-3 py-2.5 text-sm font-medium text-sun-300 hover:bg-slate-800"
        onclick={() => (open = false)}
      >
        <Icon name="search" size={14} /> {t('search.all', { q: query.trim() })}
      </a>
    </div>
  {/if}
</div>
