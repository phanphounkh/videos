<script lang="ts">
  /**
   * The left navigation. Two shapes: the Canva-style rail (an icon with its label under
   * it, narrow) and the wide list. Both: Create, the main places, trash, settings,
   * storage, and your avatar at the bottom.
   */
  import { t } from '$lib/i18n/index.svelte';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import { bytes } from '$lib/format';
  import ProfileMenu from '$lib/components/account/ProfileMenu.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import type { Storage } from '$lib/types/api';

  let {
    onnavigate = () => {},
    collapsed = false,
    ontoggle = undefined,
    showProfile = true
  }: { onnavigate?: () => void; collapsed?: boolean; ontoggle?: () => void; showProfile?: boolean } = $props();

  let storage = $state<Storage | null>(null);
  // Reloaded when you move around, so the bar follows uploads and deletions.
  $effect(() => {
    void page.url.pathname;
    if (auth.user) api.storage().then((s) => (storage = s)).catch(() => {});
  });

  const path = $derived(page.url.pathname);
  const inTrash = $derived(path === '/projects' && page.url.searchParams.get('view') === 'trash');
  const MAIN: { href: string; label: string; icon: IconName; on: boolean }[] = $derived([
    { href: '/', label: t('shell.home'), icon: 'home', on: path === '/' },
    { href: '/projects', label: t('shell.projects'), icon: 'folder', on: path.startsWith('/projects') && !inTrash },
    { href: '/templates', label: t('shell.templates'), icon: 'templates', on: path.startsWith('/templates') }
  ]);
  const MORE: { href: string; label: string; icon: IconName; on: boolean }[] = $derived([
    { href: '/projects?view=trash', label: t('shell.trash'), icon: 'trash', on: inTrash },
    { href: '/settings', label: t('shell.settings'), icon: 'settings', on: path.startsWith('/settings') }
  ]);
  const share = $derived(storage ? Math.min(100, (storage.used_bytes / storage.limit_bytes) * 100) : 0);
  const storageText = $derived(
    storage ? t('shell.storageUsed', { used: bytes(storage.used_bytes), limit: bytes(storage.limit_bytes) }) : t('shell.storage')
  );

  const wide = (on: boolean) =>
    `flex h-10 items-center gap-3 rounded-xl px-3 text-sm font-medium transition ${
      on ? 'bg-sun-400/12 text-sun-200' : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100'
    }`;
</script>

{#snippet toggle()}
  {#if ontoggle}
    <button
      type="button"
      class="grid h-9 w-9 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
      aria-label={collapsed ? t('shell.expand') : t('shell.collapse')}
      aria-expanded={!collapsed}
      title={collapsed ? t('shell.expand') : t('shell.collapse')}
      onclick={ontoggle}><Icon name="panelLeft" size={19} /></button
    >
  {/if}
{/snippet}

{#if collapsed}
  <!-- the rail: icon above its label -->
  <div class="flex h-full flex-col items-center gap-1 px-1.5 py-3">
    {@render toggle()}

    <a href="/create" class="group mt-3 mb-2 flex flex-col items-center gap-1" onclick={onnavigate} aria-label={t('shell.createVideo')}>
      <span class="grid h-11 w-11 place-items-center rounded-full bg-[image:var(--sun-gradient)] text-sun-950 shadow-glow transition group-hover:scale-105"><Icon name="plus" size={22} /></span>
      <span class="text-[11px] font-medium text-slate-300">{t('shell.create')}</span>
    </a>

    {#each MAIN as item (item.href)}
      <a href={item.href} aria-current={item.on ? 'page' : undefined} class="group flex w-full flex-col items-center gap-1 py-1" onclick={onnavigate}>
        <span class="grid h-10 w-10 place-items-center rounded-xl transition {item.on ? 'bg-sun-400/15 text-sun-200' : 'text-slate-400 group-hover:bg-slate-800 group-hover:text-slate-100'}"><Icon name={item.icon} size={20} /></span>
        <span class="text-[11px] font-medium {item.on ? 'text-sun-200' : 'text-slate-400'}">{item.label}</span>
      </a>
    {/each}

    <div class="flex-1"></div>

    {#each MORE as item (item.href)}
      <a href={item.href} aria-current={item.on ? 'page' : undefined} class="group flex w-full flex-col items-center gap-1 py-1" onclick={onnavigate}>
        <span class="grid h-10 w-10 place-items-center rounded-xl transition {item.on ? 'bg-sun-400/15 text-sun-200' : 'text-slate-400 group-hover:bg-slate-800 group-hover:text-slate-100'}"><Icon name={item.icon} size={20} /></span>
        <span class="text-[11px] font-medium {item.on ? 'text-sun-200' : 'text-slate-400'}">{item.label}</span>
      </a>
    {/each}
    <a href="/settings?tab=usage" class="group flex w-full flex-col items-center gap-1 py-1" title={storageText} aria-label={t('shell.storage')} onclick={onnavigate}>
      <span class="relative grid h-10 w-10 place-items-center rounded-xl text-slate-400 transition group-hover:bg-slate-800 group-hover:text-slate-100">
        <Icon name="cloud" size={20} />
        <span class="absolute inset-x-2 bottom-1 h-0.5 overflow-hidden rounded-full bg-slate-700"><span class="block h-full {share >= 90 ? 'bg-red-400' : 'bg-sun-400'}" style="width:{Math.max(share, storage ? 8 : 0)}%"></span></span>
      </span>
      <span class="text-[11px] font-medium text-slate-400">{t('shell.storage')}</span>
    </a>
    {#if showProfile}<div class="mt-2"><ProfileMenu placement="side" /></div>{/if}
  </div>
{:else}
  <!-- the wide list -->
  <div class="flex h-full flex-col gap-1 p-3">
    <div class="mb-3 flex items-center justify-between px-2 pt-1">
      <a href="/" class="flex" aria-label={t('shell.sorya')} onclick={onnavigate}><Logo size={26} /></a>
      {@render toggle()}
    </div>

    <a href="/create" class="mb-3 block" onclick={onnavigate} aria-label={t('shell.createVideo')}>
      <span class="flex"><Button icon="plus" class="w-full">{t('shell.createVideo')}</Button></span>
    </a>

    <nav class="flex flex-col gap-0.5" aria-label={t('shell.nav')}>
      {#each MAIN as item (item.href)}
        <a href={item.href} aria-current={item.on ? 'page' : undefined} class={wide(item.on)} onclick={onnavigate}><Icon name={item.icon} size={17} />{item.label}</a>
      {/each}
    </nav>

    <div class="flex-1"></div>

    <nav class="flex flex-col gap-0.5" aria-label={t('shell.account')}>
      {#each MORE as item (item.href)}
        <a href={item.href} aria-current={item.on ? 'page' : undefined} class={wide(item.on)} onclick={onnavigate}><Icon name={item.icon} size={17} />{item.label}</a>
      {/each}
    </nav>

    <a href="/settings?tab=usage" class="mt-2 block rounded-xl border border-slate-800 p-3 transition hover:border-slate-700" onclick={onnavigate}>
      <p class="flex items-center gap-1.5 text-xs font-medium text-slate-300"><Icon name="cloud" size={14} /> {t('shell.storage')}</p>
      <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-slate-800" role="progressbar" aria-label={t('shell.storageBar')} aria-valuenow={Math.round(share)} aria-valuemin="0" aria-valuemax="100">
        <div class="h-full rounded-full {share >= 90 ? 'bg-red-400' : 'bg-[image:var(--sun-gradient)]'}" style="width:{Math.max(share, storage ? 2 : 0)}%"></div>
      </div>
      <p class="mt-1.5 text-[11px] text-slate-500">{storage ? storageText : t('common.loading')}</p>
    </a>
    {#if showProfile}<div class="mt-2 border-t border-slate-800 pt-2"><ProfileMenu placement="side" showName /></div>{/if}
  </div>
{/if}
