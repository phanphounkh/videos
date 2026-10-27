<script lang="ts">
  /**
   * Home, laid out like Canva's: a gradient banner with one big question and a search,
   * a row of round shortcuts for what to make, your recent work, a carousel of templates,
   * and the template categories as cards. Everything leads to Create, a project or a template.
   */
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import { ago, length, mmss } from '$lib/format';
  import { i18n, t } from '$lib/i18n/index.svelte';
  import { reveal } from '$lib/actions/reveal';
  import AnimatedThumb from '$lib/components/home/AnimatedThumb.svelte';
  import HostAvatar from '$lib/components/home/HostAvatar.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import SearchBox from '$lib/components/shell/SearchBox.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';
  import { saveDraft } from '$lib/stores/draft';
  import { auth } from '$lib/stores/auth.svelte';
  import { CATEGORY_CARDS, matches, toQuery } from '$lib/templates';
  import type { ActivityItem, Project, TemplateItem } from '$lib/types/api';

  // The round shortcuts under the search. `label` is a dictionary key.
  const SHORTCUTS: { label: string; icon: IconName; href: string; tone: string }[] = [
    { label: 'home.fmt.ai.label', icon: 'sparkles', href: '/create/ai', tone: 'from-amber-400 to-orange-500 text-white' },
    { label: 'home.sc.templates', icon: 'templates', href: '/templates', tone: 'from-slate-600 to-slate-700 text-slate-100' },
    { label: 'home.fmt.social.label', icon: 'phone', href: '/create?aspect=9:16', tone: 'from-rose-500 to-pink-500 text-white' },
    { label: 'home.fmt.blank.label', icon: 'video', href: '/create?aspect=16:9', tone: 'from-fuchsia-500 to-purple-600 text-white' },
    { label: 'home.fmt.youtube.label', icon: 'monitor', href: '/create?aspect=16:9', tone: 'from-red-500 to-red-600 text-white' },
    { label: 'home.fmt.import.label', icon: 'upload', href: '/create?import=1', tone: 'from-slate-600 to-slate-700 text-slate-100' }
  ];

  /** The translated name for backend-supplied content, falling back to the API's own text. */
  const name = (key: string, fallback: string) => {
    const s = t(key);
    return s === key ? fallback : s;
  };

  let projects = $state<Project[] | null>(null);
  let templates = $state<TemplateItem[]>([]);
  let activity = $state<ActivityItem[]>([]);
  let error = $state<unknown>(null);

  // The animated host only on wide screens, so phones never download React for it.
  let wide = $state(false);
  // The demo video, offered once its file is really there.
  let demoReady = $state(false);
  let demoOpen = $state(false);
  let demoLang = $state<'en' | 'km'>('en');
  $effect(() => {
    wide = matchMedia('(min-width: 1280px)').matches;
    demoLang = i18n.locale;
    fetch('/demo/sorya-demo-en.mp4', { method: 'HEAD' }).then((r) => (demoReady = r.ok)).catch(() => {});
  });
  // The card under the pointer (or focus): its cover plays.
  let hot = $state<string | null>(null);
  let forYou = $state<HTMLElement | undefined>();
  let browse = $state<HTMLElement | undefined>();

  $effect(() => {
    if (!auth.ready) return;
    if (!auth.user) {
      void goto('/login', { replaceState: true });
      return;
    }
    api.listProjects().then((p) => (projects = p.items)).catch((e) => ((projects = []), (error = e)));
    api.templates().then((r) => (templates = r.templates)).catch(() => {});
    api.activity().then((a) => (activity = a)).catch(() => {});
  });

  const recent = $derived((projects ?? []).slice(0, 6));
  const templateFor = (filter: (typeof CATEGORY_CARDS)[number]['filter']) =>
    templates.find((x) => matches(x, filter));

  function useTemplate(x: TemplateItem) {
    saveDraft({ prompt: x.prompt, purpose: x.purpose, aspect: x.aspect_ratio, duration: x.duration });
    void goto(`/create/ai?purpose=${x.purpose}`);
  }
  const scroll = (el: HTMLElement | undefined, by: number) => el?.scrollBy({ left: by, behavior: 'smooth' });
</script>

<svelte:head><title>{t('home.title')} · Sorya</title></svelte:head>

{#if auth.user}
  <main class="mx-auto flex max-w-[120rem] flex-col gap-10 px-4 py-6 sm:px-6 lg:px-10">
    <!-- the banner -->
    <section
      class="relative isolate overflow-hidden rounded-3xl border border-slate-800 bg-gradient-to-br from-teal-400/20 via-slate-950 to-fuchsia-500/20 px-4 pt-12 pb-8 sm:px-8 sm:pt-14 xl:grid xl:grid-cols-[minmax(0,1fr)_21rem] xl:items-end xl:gap-6 xl:pb-0 2xl:grid-cols-[minmax(0,1fr)_26rem]"
    >
      <div class="animate-drift-a pointer-events-none absolute -top-24 left-1/4 -z-10 h-72 w-72 rounded-full bg-teal-400/20 blur-3xl"></div>
      <div class="animate-drift-b pointer-events-none absolute -top-16 right-1/5 -z-10 h-72 w-72 rounded-full bg-fuchsia-500/20 blur-3xl"></div>
      <div class="min-w-0 xl:pb-8">
      <h1 class="animate-fade-up text-center text-3xl leading-tight font-bold tracking-tight text-slate-50 sm:text-5xl">
        {t('home.hero.before')}<span class="bg-[image:var(--sun-gradient)] bg-clip-text text-transparent">{t('home.hero.brand')}</span>{t('home.hero.after')}
      </h1>

      <div class="animate-fade-up mt-5 flex justify-center gap-2" style="animation-delay:90ms" role="navigation" aria-label={t('shell.nav')}>
        <span class="inline-flex h-9 items-center gap-2 rounded-full border border-sun-400 bg-sun-400/15 px-4 text-sm font-medium text-sun-100"><Icon name="home" size={15} />{t('home.pill.home')}</span>
        <a href="/templates" class="inline-flex h-9 items-center gap-2 rounded-full border border-slate-700 bg-slate-900/60 px-4 text-sm font-medium text-slate-300 transition hover:border-slate-500 hover:text-slate-50"><Icon name="templates" size={15} />{t('home.pill.templates')}</a>
        {#if demoReady}
          <button type="button" class="inline-flex h-9 items-center gap-2 rounded-full bg-[image:var(--sun-gradient)] px-4 text-sm font-semibold text-sun-950 shadow-glow transition hover:scale-105" onclick={() => (demoOpen = true)}><Icon name="play" size={14} />{t('home.demo.watch')}</button>
        {/if}
      </div>


      <div class="animate-fade-up mt-6 flex justify-center" style="animation-delay:170ms">
        <SearchBox large placeholder={t('home.search')} />
      </div>

      <!-- first/last auto margins centre the row without clipping its start when it scrolls -->
      <ul class="mt-8 flex gap-1 overflow-x-auto pb-1 [&>li:first-child]:ml-auto [&>li:last-child]:mr-auto" aria-label={t('home.shortcuts')}>
        {#each SHORTCUTS as s, i (s.label)}
          <li class="animate-pop-in shrink-0" style="animation-delay:{260 + i * 70}ms">
            <a href={s.href} class="group flex w-24 flex-col items-center gap-2.5 rounded-2xl px-1 py-2 text-center 2xl:w-32">
              <span class="grid h-16 w-16 place-items-center rounded-full bg-gradient-to-br shadow-lg shadow-black/30 transition group-hover:-translate-y-0.5 group-hover:scale-105 {s.tone}"><Icon name={s.icon} size={26} /></span>
              <span class="text-[13px] leading-tight font-medium text-slate-200">{t(s.label)}</span>
            </a>
          </li>
        {/each}
      </ul>
      </div>
      <!-- the host gets its own column on wide screens, standing on the banner's floor -->
      {#if wide}<div class="relative z-0 -mr-2 hidden self-end xl:block"><HostAvatar /></div>{/if}
    </section>

    <ErrorBanner {error} />

    <!-- continue editing -->
    {#if projects === null || recent.length}
      <section aria-labelledby="continue" use:reveal>
        <div class="mb-3 flex items-end justify-between">
          <h2 id="continue" class="text-2xl font-bold tracking-tight text-slate-50">{t('home.continue')}</h2>
          {#if projects?.length}<a href="/projects" class="text-sm font-medium text-slate-300 hover:text-sun-200">{t('common.seeAll')}</a>{/if}
        </div>
        {#if projects === null}
          <div class="grid gap-4 sm:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6" aria-busy="true">{#each [0, 1, 2, 3, 4, 5] as n (n)}<div class="aspect-video animate-pulse rounded-2xl bg-slate-800/60"></div>{/each}</div>
        {:else}
          <ul class="grid grid-cols-2 gap-4 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
            {#each recent as p (p.id)}
              <li>
                <a href="/projects/{p.id}" class="group block" aria-label={t('home.open', { title: p.title })}>
                  <div class="relative aspect-video overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 transition group-hover:border-slate-500">
                    {#if p.thumbnail_url}<img src={p.thumbnail_url} alt="" loading="lazy" class="h-full w-full object-contain" />{:else}<div class="grid h-full place-items-center text-slate-600"><Icon name="film" size={28} /></div>{/if}
                    <span class="absolute right-2 bottom-2 rounded-md bg-slate-950/80 px-1.5 py-0.5 font-mono text-xs text-slate-100">{mmss(p.duration)}</span>
                  </div>
                  <p class="mt-2 line-clamp-1 font-semibold text-slate-50 group-hover:text-sun-300" data-private>{p.title}</p>
                  <p class="text-xs text-slate-500">{t('home.edited', { when: ago(p.updated_at) })}</p>
                </a>
              </li>
            {/each}
          </ul>
        {/if}
      </section>
    {:else}
      <section use:reveal class="mx-1 flex flex-col items-center gap-3 rounded-2xl border border-dashed border-slate-700 px-6 py-10 text-center">
        <Logo size={36} wordmark={false} />
        <p class="font-semibold text-slate-50">{t('home.empty.title')}</p>
        <p class="max-w-md text-sm text-slate-400">{t('home.empty.body')}</p>
      </section>
    {/if}

    <!-- templates for you -->
    {#if templates.length}
      <section aria-labelledby="foryou" use:reveal>
        <div class="mb-3 flex items-end justify-between">
          <h2 id="foryou" class="text-2xl font-bold tracking-tight text-slate-50">{t('home.forYou')}</h2>
          <a href="/templates" class="text-sm font-medium text-slate-300 hover:text-sun-200">{t('common.seeAll')}</a>
        </div>
        <div class="relative">
          <ul bind:this={forYou} class="scrollbar-none -mx-1 flex snap-x gap-4 overflow-x-auto px-1 pb-2">
            {#each templates as x (x.key)}
              {@const [w, h] = x.aspect_ratio.split(':').map(Number)}
              <li class="shrink-0 snap-start">
                <button type="button" class="group relative block h-60 overflow-hidden rounded-2xl border border-slate-800 bg-slate-950 transition hover:border-slate-500 hover:shadow-pop sm:h-64" style="aspect-ratio:{w}/{h}" onclick={() => useTemplate(x)} onpointerenter={() => (hot = x.key)} onpointerleave={() => (hot = null)} onfocus={() => (hot = x.key)} onblur={() => (hot = null)} aria-label={t('templates.use', { title: name(`tpl.${x.key}.title`, x.title) })}>
                  <AnimatedThumb template={x} active={hot === x.key} />
                  <span class="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 to-transparent px-3 pt-8 pb-2.5 text-left">
                    <span class="block text-sm font-semibold text-white">{name(`tpl.${x.key}.title`, x.title)}</span>
                    <span class="text-xs text-slate-300">{x.aspect_ratio} · {length(x.duration)}</span>
                  </span>
                </button>
              </li>
            {/each}
          </ul>
          <button type="button" class="absolute top-1/2 -right-1 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-slate-700 bg-slate-900/95 text-slate-100 shadow-lg backdrop-blur transition hover:bg-slate-800 sm:grid" aria-label={t('home.next')} onclick={() => scroll(forYou, 600)}><Icon name="arrowRight" size={18} /></button>
        </div>
      </section>

      <!-- browse template categories -->
      <section aria-labelledby="browse" use:reveal>
        <h2 id="browse" class="mb-3 text-2xl font-bold tracking-tight text-slate-50">{t('home.browse')}</h2>
        <div class="relative">
          <ul bind:this={browse} class="scrollbar-none -mx-1 grid snap-x auto-cols-[15rem] grid-flow-col grid-rows-2 gap-4 overflow-x-auto px-1 pb-2">
            {#each CATEGORY_CARDS as c (c.id)}
              {@const sample = templateFor(c.filter)}
              <li class="snap-start">
                <a href="/templates{toQuery(c.filter)}" onpointerenter={() => (hot = `cat-${c.id}`)} onpointerleave={() => (hot = null)} onfocus={() => (hot = `cat-${c.id}`)} onblur={() => (hot = null)} class="group relative flex h-24 items-center overflow-hidden rounded-2xl border border-slate-800 bg-gradient-to-br px-4 transition hover:border-slate-500 {c.tint}">
                  <span class="z-10 w-2/5 text-[15px] leading-snug font-semibold text-slate-50">{t(`home.cat.${c.id}`)}</span>
                  {#if sample}<span class="absolute -right-2 -bottom-3 h-20 rotate-6 overflow-hidden rounded-lg shadow-xl shadow-black/40 transition group-hover:rotate-3 group-hover:scale-105" style="aspect-ratio:{sample.aspect_ratio.replace(':', '/')}"><AnimatedThumb template={sample} active={hot === `cat-${c.id}`} /></span>{/if}
                </a>
              </li>
            {/each}
          </ul>
          <button type="button" class="absolute top-1/2 -right-1 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full border border-slate-700 bg-slate-900/95 text-slate-100 shadow-lg backdrop-blur transition hover:bg-slate-800 sm:grid" aria-label={t('home.next')} onclick={() => scroll(browse, 520)}><Icon name="arrowRight" size={18} /></button>
        </div>
      </section>
    {/if}

    <!-- activity -->
    {#if activity.length}
      <section aria-labelledby="activity" use:reveal>
        <h2 id="activity" class="mb-3 text-2xl font-bold tracking-tight text-slate-50">{t('home.activity')}</h2>
        <ul class="grid gap-x-10 md:grid-cols-2">
          {#each activity as a (a.kind + a.project_id + a.at)}
            <li class="border-b border-slate-800">
              <a href="/projects/{a.project_id}" class="flex items-center gap-3 py-3 text-sm hover:text-sun-200">
                <span class="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-slate-800 text-slate-400"><Icon name={a.kind === 'exported' ? 'download' : 'film'} size={15} /></span>
                <span class="min-w-0 flex-1 truncate text-slate-300">{t(a.kind === 'exported' ? 'home.activity.exported' : 'home.activity.created')} <strong class="font-semibold text-slate-100" data-private>{a.title}</strong></span>
                <span class="shrink-0 text-xs text-slate-500">{ago(a.at)}</span>
              </a>
            </li>
          {/each}
        </ul>
      </section>
    {/if}
  </main>
{/if}

{#if demoOpen}
  <Modal title={t('home.demo.title')} onclose={() => (demoOpen = false)} wide>
    <div class="overflow-hidden rounded-xl bg-black">
      {#key demoLang}
        <!-- svelte-ignore a11y_media_has_caption -->
        <video
          class="aspect-video w-full"
          src="/demo/sorya-demo-{demoLang}.mp4"
          poster="/demo/sorya-demo-{demoLang}.jpg"
          controls
          autoplay
          playsinline
        ></video>
      {/key}
    </div>
    <div class="mt-3 flex items-center justify-between gap-3 text-xs text-slate-400">
      <span>{t('home.demo.language')}</span>
      <span class="inline-flex rounded-lg border border-slate-700 bg-slate-950 p-0.5">
        {#each [['en', 'English'], ['km', 'ខ្មែរ']] as [code, label] (code)}
          <button type="button" class="rounded-md px-3 py-1 text-sm font-medium transition {demoLang === code ? 'bg-slate-700 text-slate-50' : 'text-slate-400 hover:text-slate-200'}" onclick={() => (demoLang = code as 'en' | 'km')}>{label}</button>
        {/each}
      </span>
    </div>
    {#snippet actions()}
      <button type="button" class="rounded-lg border border-slate-700 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-800" onclick={() => (demoOpen = false)}>{t('home.demo.close')}</button>
    {/snippet}
  </Modal>
{/if}
