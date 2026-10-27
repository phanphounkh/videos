<script lang="ts">
  /**
   * The avatar in the navbar and the menu under it, like CapCut, Canva or ChatGPT: who you
   * are and your plan, your latest videos, Settings, Usage, and Log out.
   */
  import { t, tn } from '$lib/i18n/index.svelte';
  import { api } from '$lib/api';
  import Avatar from '$lib/components/ui/Avatar.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import LanguageSwitch from '$lib/components/ui/LanguageSwitch.svelte';
  import { auth, logout } from '$lib/stores/auth.svelte';
  import type { Project } from '$lib/types/api';

  /** `side`: opens to the right of a sidebar avatar, growing upwards. */
  let { placement = 'down', showName = false }: { placement?: 'down' | 'side'; showName?: boolean } = $props();

  let open = $state(false);
  let recent = $state<Project[] | null>(null);
  let root = $state<HTMLElement | undefined>();

  const user = $derived(auth.user);
  const name = $derived(user?.full_name?.trim() || user?.email.split('@')[0] || '');

  async function toggle() {
    open = !open;
    // Loaded on first open, and again each time so "recent" really is recent.
    if (open) {
      try {
        recent = (await api.listProjects()).items.slice(0, 4);
      } catch {
        recent = recent ?? [];
      }
    }
  }

  const close = () => (open = false);

  $effect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => {
      if (root && !root.contains(e.target as Node)) close();
    };
    const key = (e: KeyboardEvent) => e.key === 'Escape' && close();
    document.addEventListener('pointerdown', away);
    document.addEventListener('keydown', key);
    return () => {
      document.removeEventListener('pointerdown', away);
      document.removeEventListener('keydown', key);
    };
  });
</script>

{#if user}
  <div class="relative {showName ? 'w-full' : ''}" bind:this={root}>
    {#if showName}
      <!-- the wide sidebar: your picture, your name, your email -->
      <button
        type="button"
        class="flex w-full items-center gap-3 rounded-xl px-2 py-2 text-left transition hover:bg-slate-800 {open ? 'bg-slate-800' : ''}"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t('menu.account')}
        data-track="profile menu"
        onclick={toggle}
      >
        <Avatar {user} size={36} />
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-semibold text-slate-100" data-private>{name}</span>
          <span class="block truncate text-xs text-slate-500" data-private>{user.email}</span>
        </span>
        <Icon name="chevronUp" size={15} class="shrink-0 text-slate-500" />
      </button>
    {:else}
      <!-- the rail / top bar: just the circle -->
      <button
        type="button"
        class="grid place-items-center rounded-full ring-offset-2 ring-offset-slate-950 transition hover:ring-2 hover:ring-sun-400/60 focus-visible:ring-2 focus-visible:ring-sun-400 {open ? 'ring-2 ring-sun-400' : ''}"
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t('menu.account')}
        title={name}
        data-track="profile menu"
        onclick={toggle}
      >
        <Avatar {user} size={36} />
      </button>
    {/if}

    {#if open}
      <div
        role="menu"
        class="absolute z-50 w-72 overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-2xl shadow-black/50 {placement === 'side' ? 'bottom-0 left-full ml-3' : 'right-0 mt-2'}"
      >
        <div class="flex items-center gap-3 border-b border-slate-800 p-4">
          <Avatar {user} size={44} />
          <div class="min-w-0">
            <p class="truncate text-sm font-semibold text-slate-50" data-private>{name}</p>
            <p class="truncate text-xs text-slate-400" data-private>{user.email}</p>
            <span
              class="mt-1 inline-block rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-medium text-slate-300 capitalize"
              >{t('menu.plan', { plan: user.plan })}</span
            >
          </div>
        </div>

        <div class="border-b border-slate-800 p-2" data-private>
          <p class="px-2 pt-1 pb-1.5 text-[11px] font-semibold tracking-wide text-slate-500 uppercase">
            {t('menu.recent')}
          </p>
          {#if recent === null}
            <p class="px-2 py-3 text-xs text-slate-500">{t('common.loading')}</p>
          {:else if !recent.length}
            <p class="px-2 py-3 text-xs text-slate-500">{t('menu.noVideos')}</p>
          {:else}
            <ul>
              {#each recent as project (project.id)}
                <li>
                  <a
                    role="menuitem"
                    href="/projects/{project.id}"
                    class="flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition hover:bg-slate-800"
                    onclick={close}
                  >
                    <span
                      class="grid h-9 w-14 shrink-0 place-items-center overflow-hidden rounded-md bg-slate-800 text-slate-500"
                    >
                      {#if project.thumbnail_url}
                        <img src={project.thumbnail_url} alt="" class="h-full w-full object-cover" />
                      {:else}
                        <Icon name="film" size={15} />
                      {/if}
                    </span>
                    <span class="min-w-0 flex-1">
                      <span class="block truncate text-sm text-slate-100">{project.title}</span>
                      <span class="block text-[11px] text-slate-500 capitalize"
                        >{t(`status.${project.status.toLowerCase()}`)} · {tn('menu.scenes', project.scene_count)}</span
                      >
                    </span>
                  </a>
                </li>
              {/each}
            </ul>
          {/if}
          <a
            role="menuitem"
            href="/projects"
            class="mt-1 block rounded-lg px-2 py-1.5 text-xs font-medium text-sun-300 hover:bg-slate-800"
            onclick={close}>{t('menu.allProjects')}</a
          >
        </div>

        <div class="p-2">
          {#each [{ href: '/settings?tab=usage', label: t('menu.usage'), icon: 'clock' as const }, { href: '/settings', label: t('menu.settings'), icon: 'user' as const }] as item (item.href)}
            <a
              role="menuitem"
              href={item.href}
              class="flex items-center gap-2.5 rounded-lg px-2 py-2 text-sm text-slate-200 transition hover:bg-slate-800"
              onclick={close}><Icon name={item.icon} size={15} /> {item.label}</a
            >
          {/each}
          <div class="flex items-center justify-between gap-3 px-2 py-2">
            <span class="text-sm text-slate-300">{t('menu.language')}</span>
            <LanguageSwitch />
          </div>
          <button
            type="button"
            role="menuitem"
            class="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left text-sm text-slate-200 transition hover:bg-slate-800"
            onclick={() => {
              close();
              void logout();
            }}><Icon name="logout" size={15} /> {t('menu.logout')}</button
          >
        </div>
      </div>
    {/if}
  </div>
{/if}
