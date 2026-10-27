<script lang="ts">
  /**
   * A grid of hosts to choose from: the user's own uploads first, then the built-in ones
   * (filterable by style, gender and age), and a card to upload another. One card is
   * selected; arrow keys move between cards (radio-style), Enter or Space chooses.
   */
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Menu from '$lib/components/ui/Menu.svelte';
  import { t } from '$lib/i18n/index.svelte';
  import type { CustomAvatar } from '$lib/types/api';
  import AnimatedAvatar from './AnimatedAvatar.svelte';
  import AvatarActions from './AvatarActions.svelte';
  import AvatarImage from './AvatarImage.svelte';
  import AvatarUploadDialog from './AvatarUploadDialog.svelte';
  import { builtinHosts, customHosts, hostPrefs, hosts, loadHosts } from './hosts.svelte';

  let {
    value,
    onselect,
    allowAuto = false,
    autoLabel = undefined,
    autoHint = undefined,
    manage = true,
    size = 'md'
  }: {
    /** The chosen host id, or null for "automatic". */
    value: string | null;
    onselect: (id: string | null) => void;
    /** Offer an "Automatic" card meaning null. */
    allowAuto?: boolean;
    autoLabel?: string;
    autoHint?: string;
    /** Show the edit/delete menu on uploaded hosts. */
    manage?: boolean;
    /** `lg` for the full-width Settings page, `md` inside dialogs. */
    size?: 'md' | 'lg';
  } = $props();

  // The card under the pointer (or focus): its host plays.
  let hot = $state<string | null>(null);

  $effect(() => {
    void loadHosts();
  });

  let style = $state<'all' | 'toon' | 'real'>('all');
  let gender = $state<'all' | 'male' | 'female'>('all');
  let age = $state<'all' | 'young' | 'adult' | 'old'>('all');
  let uploading = $state(false);
  let editing = $state<CustomAvatar | null>(null);
  let deleting = $state<CustomAvatar | null>(null);
  let grid = $state<HTMLElement>();

  const shown = $derived(
    builtinHosts().filter(
      (a) => (style === 'all' || a.style === style) && (gender === 'all' || a.gender === gender) && (age === 'all' || a.age === age)
    )
  );
  const custom = $derived(customHosts());
  const favourite = $derived(hostPrefs().default);

  const filters = $derived([
    {
      key: 'style',
      label: t('avatars.filter.style'),
      options: [
        ['all', t('avatars.all')],
        ['toon', t('avatars.style.toon')],
        ['real', t('avatars.style.real')]
      ]
    },
    {
      key: 'gender',
      label: t('avatars.filter.gender'),
      options: [
        ['all', t('avatars.all')],
        ['male', t('avatars.gender.male')],
        ['female', t('avatars.gender.female')]
      ]
    },
    {
      key: 'age',
      label: t('avatars.filter.age'),
      options: [
        ['all', t('avatars.all')],
        ['young', t('avatars.age.young')],
        ['adult', t('avatars.age.adult')],
        ['old', t('avatars.age.old')]
      ]
    }
  ] as { key: 'style' | 'gender' | 'age'; label: string; options: [string, string][] }[]);
  const current = (key: 'style' | 'gender' | 'age') => ({ style, gender, age })[key];
  function pick(key: 'style' | 'gender' | 'age', value: string) {
    if (key === 'style') style = value as typeof style;
    else if (key === 'gender') gender = value as typeof gender;
    else age = value as typeof age;
  }

  /** Radio-style keys: arrows move focus to the neighbouring card. */
  function keys(e: KeyboardEvent) {
    const move = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!move || !grid) return;
    const radios = [...grid.querySelectorAll<HTMLButtonElement>('[role="radio"], [data-nav]')];
    const at = radios.indexOf(document.activeElement as HTMLButtonElement);
    if (at < 0) return;
    e.preventDefault();
    radios[(at + move + radios.length) % radios.length]?.focus();
  }

  // One card is in the tab order: the selected one, else the first.
  const tabbable = $derived(
    value !== null && (custom.some((c) => c.id === value) || shown.some((a) => a.id === value))
      ? value
      : allowAuto
        ? '__auto'
        : (custom[0]?.id ?? shown[0]?.id ?? '__upload')
  );

  const lg = $derived(size === 'lg');
  /** One card: a tinted stage for the picture, then the name and its tags. */
  const card = (on: boolean) =>
    `group relative flex h-full w-full flex-col overflow-hidden rounded-2xl border text-center transition duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sun-400 hover:-translate-y-0.5 ${
      on ? 'border-sun-400 shadow-glow ring-2 ring-sun-400/70' : 'border-slate-800 hover:border-slate-500 hover:shadow-pop'
    } bg-slate-900`;
  const stage = (style: string) =>
    `relative block w-full aspect-[4/5] overflow-hidden ${
      style === 'real'
        ? 'bg-gradient-to-b from-sky-400/25 via-slate-800 to-slate-900'
        : 'bg-gradient-to-b from-amber-400/30 via-orange-500/10 to-slate-900'
    }`;
  const chip = 'rounded-full bg-slate-800 px-2 py-0.5 text-[10px] leading-4 font-medium text-slate-300';
  const gridClass = $derived(
    lg
      ? 'grid grid-cols-[repeat(auto-fill,minmax(11rem,1fr))] gap-4'
      : 'grid grid-cols-[repeat(auto-fill,minmax(7.75rem,1fr))] gap-3'
  );
</script>

{#snippet fav(id: string)}
  {#if favourite === id}
    <span class="absolute top-2 left-2 z-10 inline-flex items-center gap-1 rounded-full bg-sun-500 px-2 py-0.5 text-[10px] font-bold text-sun-950 shadow" title={t('avatars.favourite')}>
      ★ <span>{t('avatars.favourite')}</span>
    </span>
  {/if}
{/snippet}

{#snippet tick(on: boolean)}
  {#if on}
    <span class="absolute right-2 bottom-2 z-10 grid h-6 w-6 place-items-center rounded-full bg-sun-400 text-sun-950 shadow-lg" aria-hidden="true"><Icon name="check" size={14} /></span>
  {/if}
{/snippet}

<div class="flex flex-col gap-5">
  <ErrorBanner error={hosts.error} />

  <div class="flex flex-wrap items-center gap-x-5 gap-y-2.5">
    {#each filters as f (f.key)}
      <div class="flex items-center gap-2" role="radiogroup" aria-label={f.label}>
        <span class="text-xs font-medium text-slate-500">{f.label}</span>
        <div class="inline-flex rounded-full border border-slate-700 bg-slate-900 p-0.5">
          {#each f.options as [v, label] (v)}
            <button
              type="button"
              role="radio"
              aria-checked={current(f.key) === v}
              class="rounded-full px-3 py-1 text-xs font-medium whitespace-nowrap transition {current(f.key) === v ? 'bg-slate-700 text-slate-50 shadow-sm' : 'text-slate-400 hover:text-slate-200'}"
              onclick={() => pick(f.key, v)}>{label}</button
            >
          {/each}
        </div>
      </div>
    {/each}
  </div>

  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="flex flex-col gap-6" bind:this={grid} onkeydown={keys}>
    {#if allowAuto}
      <div role="radiogroup" aria-label={t('avatars.title')}>
        <button
          type="button"
          role="radio"
          aria-checked={value === null}
          tabindex={tabbable === '__auto' ? 0 : -1}
          class="flex w-full items-center gap-3 rounded-2xl border px-4 py-3 text-left transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sun-400 {value === null ? 'border-sun-400 bg-sun-500/10 ring-2 ring-sun-400/60' : 'border-slate-800 bg-slate-900 hover:border-slate-600'}"
          onclick={() => onselect(null)}
        >
          <span class="grid h-10 w-10 shrink-0 place-items-center rounded-full bg-slate-800 text-sun-300"><Icon name="sparkles" size={18} /></span>
          <span class="min-w-0 flex-1">
            <span class="block text-sm font-semibold text-slate-50">{autoLabel ?? t('avatars.automatic')}</span>
            <span class="block text-xs text-slate-400">{autoHint ?? t('avatars.automaticHint')}</span>
          </span>
          {#if value === null}<span class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-sun-400 text-sun-950" aria-hidden="true"><Icon name="check" size={14} /></span>{/if}
        </button>
      </div>
    {/if}

    {#if custom.length}
      <section class="flex flex-col gap-3">
        <h3 class="flex items-center gap-2 text-sm font-semibold text-slate-200">{t('avatars.yours')} <span class="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-400">{custom.length}</span></h3>
        <div class={gridClass} role="radiogroup" aria-label={t('avatars.yours')}>
          {#each custom as a (a.id)}
            <div class="relative h-full" onpointerenter={() => (hot = a.id)} onpointerleave={() => (hot = null)} onfocusin={() => (hot = a.id)} onfocusout={() => (hot = null)}>
              <button type="button" role="radio" aria-checked={value === a.id} tabindex={tabbable === a.id ? 0 : -1} class={card(value === a.id)} onclick={() => onselect(a.id)}>
                <span class={stage('toon')}>
                  <AvatarImage src={a.image_url} name={a.name} fit="cover" class="absolute inset-0 h-full w-full" />
                  <AnimatedAvatar id={a.id} active={hot === a.id} />
                  {@render tick(value === a.id)}
                </span>
                <span class="flex flex-col items-center gap-1.5 px-2.5 py-2.5">
                  <span class="w-full truncate text-sm font-semibold text-slate-50">{a.name}</span>
                  <span class={chip}>{t(`avatars.mode.${a.mode}`)}</span>
                </span>
              </button>
              {@render fav(a.id)}
              {#if manage}
                <Menu
                  class="absolute top-2 right-2 z-10"
                  label={t('avatars.manage', { name: a.name })}
                  items={[
                    { label: t('avatars.edit'), icon: 'pencil', onclick: () => (editing = a) },
                    { label: t('avatars.delete'), icon: 'trash', danger: true, separator: true, onclick: () => (deleting = a) }
                  ]}
                />
              {/if}
            </div>
          {/each}
        </div>
      </section>
    {/if}

    <section class="flex flex-col gap-3">
      <h3 class="flex items-center gap-2 text-sm font-semibold text-slate-200">{t('avatars.builtin')} <span class="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-400">{shown.length}</span></h3>
      <div class={gridClass} role="radiogroup" aria-label={t('avatars.builtin')}>
        {#each shown as a (a.id)}
          <div class="relative h-full" onpointerenter={() => (hot = a.id)} onpointerleave={() => (hot = null)} onfocusin={() => (hot = a.id)} onfocusout={() => (hot = null)}>
            <button type="button" role="radio" aria-checked={value === a.id} tabindex={tabbable === a.id ? 0 : -1} class={card(value === a.id)} onclick={() => onselect(a.id)}>
              <span class={stage(a.style)}>
                <AvatarImage src={a.preview_url} name={a.name} class="absolute inset-0 h-full w-full bg-transparent" />
                <AnimatedAvatar id={a.id} active={hot === a.id} />
                {@render tick(value === a.id)}
              </span>
              <span class="flex flex-col items-center gap-1.5 px-2.5 py-2.5">
                <span class="w-full truncate text-sm font-semibold text-slate-50">{a.name}</span>
                <span class="flex flex-wrap justify-center gap-1">
                  <span class={chip}>{t(`avatars.style.${a.style}`)}</span>
                  <span class={chip}>{t(`avatars.gender.${a.gender}`)}</span>
                  <span class={chip}>{t(`avatars.age.${a.age}`)}</span>
                </span>
              </span>
            </button>
            {@render fav(a.id)}
          </div>
        {/each}
        <button type="button" data-nav tabindex={tabbable === '__upload' ? 0 : -1} class="group flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed border-slate-700 bg-gradient-to-b from-slate-900 to-slate-950 p-4 text-center text-slate-400 transition hover:-translate-y-0.5 hover:border-sun-400/70 hover:text-sun-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-sun-400 {lg ? 'min-h-72' : 'min-h-44'}" onclick={() => (uploading = true)}>
          <span class="grid h-12 w-12 place-items-center rounded-full bg-slate-800 transition group-hover:bg-sun-400/20"><Icon name="upload" size={22} /></span>
          <span class="text-sm font-semibold">{t('avatars.upload')}</span>
        </button>
      </div>
      {#if !shown.length}<p class="py-4 text-center text-sm text-slate-500">{t('avatars.noMatch')}</p>{/if}
    </section>
  </div>
</div>

{#if uploading}
  <AvatarUploadDialog
    onclose={() => (uploading = false)}
    ondone={async (created) => {
      await loadHosts(true);
      uploading = false;
      onselect(created.id);
    }}
  />
{/if}
<AvatarActions bind:editing bind:deleting ondeleted={(id) => value === id && onselect(null)} />
