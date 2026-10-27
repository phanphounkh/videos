<script lang="ts">
  /** The template gallery: pick a starting point; Sorya writes the video from its idea. */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import { length } from '$lib/format';
  import { t, tn } from '$lib/i18n/index.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import AnimatedThumb from '$lib/components/home/AnimatedThumb.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import { saveDraft } from '$lib/stores/draft';
  import { cardFor, fromParams, matches, toQuery } from '$lib/templates';
  import { auth } from '$lib/stores/auth.svelte';
  import type { TemplateItem } from '$lib/types/api';

  /** The translated name for backend-supplied content, falling back to the API's own text. */
  const name = (key: string, fallback: string) => {
    const s = t(key);
    return s === key ? fallback : s;
  };

  let templates = $state<TemplateItem[] | null>(null);
  let categories = $state<string[]>([]);
  let search = $state('');
  // The card under the pointer (or focus): its cover plays.
  let hot = $state<string | null>(null);
  let error = $state<unknown>(null);

  $effect(() => {
    if (!auth.ready) return;
    if (!auth.user) {
      void goto('/login', { replaceState: true });
      return;
    }
    api
      .templates()
      .then((r) => ((templates = r.templates), (categories = r.categories)))
      .catch((e) => ((error = e), (templates = [])));
  });

  // The filter is the address (/templates?purpose=explainer), so a category card on Home is a link.
  const filter = $derived(fromParams(page.url.searchParams));
  const active = $derived(filter.category ?? 'all');
  const other = $derived({ ...filter, category: undefined });
  const hasOther = $derived(!!(other.purpose || other.aspect || other.maxSeconds));
  const otherName = $derived.by(() => {
    const card = cardFor(other);
    return card ? t(`home.cat.${card.id}`) : [other.purpose, other.aspect].filter(Boolean).join(' · ');
  });
  const setFilter = (next: typeof filter) =>
    void goto(`/templates${toQuery(next)}`, { replaceState: true, noScroll: true, keepFocus: true });

  const shown = $derived(
    (templates ?? []).filter((x) => {
      const q = search.trim().toLowerCase();
      return (
        matches(x, filter) &&
        (!q || x.title.toLowerCase().includes(q) || name(`tpl.${x.key}.title`, x.title).toLowerCase().includes(q) || x.prompt.toLowerCase().includes(q))
      );
    })
  );

  function use(x: TemplateItem) {
    saveDraft({ prompt: x.prompt, purpose: x.purpose, aspect: x.aspect_ratio, duration: x.duration });
    void goto(`/create/ai?purpose=${x.purpose}`);
  }
</script>

<svelte:head><title>{t('templates.title')} · Sorya</title></svelte:head>

<main class="mx-auto flex max-w-[120rem] flex-col gap-6 px-4 py-6 sm:px-6 lg:px-10">
  <div>
    <h1 class="text-[30px] leading-tight font-bold tracking-tight text-slate-50">{t('templates.title')}</h1>
    <p class="mt-1 text-slate-400">{t('templates.subtitle')}</p>
  </div>

  <div class="relative max-w-xl">
    <Icon name="search" size={18} class="pointer-events-none absolute top-1/2 left-4 -translate-y-1/2 text-slate-500" />
    <input type="search" bind:value={search} placeholder={t('templates.searchPlaceholder')} aria-label={t('templates.searchPlaceholder')} class="h-12 w-full rounded-full border border-slate-800 bg-slate-900 pr-5 pl-12 text-slate-100 placeholder:text-slate-500 focus:border-sun-400 focus:outline-none" />
  </div>

  {#if hasOther}
    <p class="flex items-center gap-3 text-sm text-slate-300">
      <span class="rounded-full bg-slate-800 px-3 py-1">{t('templates.filter', { name: otherName })}</span>
      <button type="button" class="font-medium text-sun-300 hover:text-sun-200" onclick={() => setFilter({ category: filter.category })}>{t('templates.clearFilter')}</button>
    </p>
  {/if}

  <div class="flex flex-wrap gap-2" role="radiogroup" aria-label={t('templates.categoryLabel')}>
    {#each ['all', ...categories] as c (c)}
      <button
        type="button"
        role="radio"
        aria-checked={active === c}
        class="h-9 rounded-full border px-4 text-sm font-medium transition {active === c ? 'border-sun-400 bg-sun-400/15 text-sun-100' : 'border-slate-700 text-slate-300 hover:border-slate-500 hover:text-slate-50'}"
        onclick={() => setFilter({ ...other, category: c === 'all' ? undefined : c })}>{name('templates.category.' + c, c)}</button
      >
    {/each}
  </div>

  <ErrorBanner {error} />

  {#if templates === null}
    <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6" aria-busy="true">
      {#each [0, 1, 2, 3] as n (n)}<div class="aspect-video animate-pulse rounded-2xl bg-slate-800/60"></div>{/each}
    </div>
  {:else}
    <ul class="grid gap-5 sm:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
      {#each shown as x (x.key)}
        <li>
          <button type="button" class="group block w-full text-left" onclick={() => use(x)} onpointerenter={() => (hot = x.key)} onpointerleave={() => (hot = null)} onfocus={() => (hot = x.key)} onblur={() => (hot = null)} aria-label={t('templates.use', { title: name('tpl.' + x.key + '.title', x.title) })}>
            <div class="relative aspect-video overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 transition group-hover:border-slate-500 group-hover:shadow-pop">
              <AnimatedThumb template={x} active={hot === x.key} fit="contain" />
              <span class="absolute right-2.5 bottom-2.5 rounded-md bg-slate-950/80 px-1.5 py-0.5 font-mono text-xs text-slate-100">{length(x.duration)}</span>
              <span class="pointer-events-none absolute inset-x-0 bottom-3 grid place-items-center opacity-0 transition group-hover:opacity-100">
                <span class="rounded-full bg-[image:var(--sun-gradient)] px-4 py-2 text-sm font-semibold text-sun-950">{t('templates.useThis')}</span>
              </span>
            </div>
            <p class="mt-2.5 font-semibold text-slate-50">{name('tpl.' + x.key + '.title', x.title)}</p>
            <p class="mt-0.5 flex items-center gap-2 text-xs text-slate-500">
              <span class="rounded-md bg-slate-800 px-1.5 py-0.5 text-slate-300">{x.aspect_ratio}</span>
              <span>{name('templates.category.' + x.category, x.category)}</span>
            </p>
          </button>
        </li>
      {:else}
        <li class="col-span-full py-12 text-center text-sm text-slate-400">{t('templates.empty')}</li>
      {/each}
    </ul>
  {/if}
</main>
