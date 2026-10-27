<script lang="ts">
  /**
   * The frame around every page outside the editor: a sidebar on the left (a drawer on
   * small screens), a top bar with search and the profile menu, and the page itself.
   */
  import { t, tn } from '$lib/i18n/index.svelte';
  import { page } from '$app/state';
  import ProfileMenu from '$lib/components/account/ProfileMenu.svelte';
  import SearchBox from '$lib/components/shell/SearchBox.svelte';
  import SidebarNav from '$lib/components/shell/SidebarNav.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';

  let { children }: { children: import('svelte').Snippet } = $props();
  let drawer = $state(false);

  // The sidebar can shrink to icons; the choice is remembered in this browser.
  const KEY = 'sorya.sidebar';
  let collapsed = $state(true);
  $effect(() => {
    try {
      // The slim rail is the default; the wide list only if it was chosen.
      collapsed = localStorage.getItem(KEY) !== 'expanded';
    } catch {
      // expanded
    }
  });
  function toggle() {
    collapsed = !collapsed;
    try {
      localStorage.setItem(KEY, collapsed ? 'collapsed' : 'expanded');
    } catch {
      // not remembered
    }
  }

  // Moving to another page closes the drawer.
  $effect(() => {
    void page.url.pathname;
    drawer = false;
  });
</script>

<div class="flex h-dvh">
  <aside
    class="hidden shrink-0 border-r border-slate-800 bg-slate-950 transition-[width] duration-200 lg:block {collapsed ? 'w-[5.25rem]' : 'w-64'}"
    aria-label={t('shell.sidebar')}
  >
    <SidebarNav {collapsed} ontoggle={toggle} />
  </aside>

  {#if drawer}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div class="fixed inset-0 z-50 bg-black/60 lg:hidden" onclick={(e) => e.target === e.currentTarget && (drawer = false)}>
      <aside class="h-full w-72 max-w-[85vw] border-r border-slate-800 bg-slate-950" aria-label={t('shell.sidebar')}>
        <SidebarNav onnavigate={() => (drawer = false)} showProfile={false} />
      </aside>
    </div>
  {/if}

  <div class="flex min-w-0 flex-1 flex-col">
    <header class="z-30 flex h-16 shrink-0 items-center lg:hidden gap-3 border-b border-slate-800 bg-slate-950/80 px-4 backdrop-blur sm:px-6">
      <button
        type="button"
        class="grid h-9 w-9 place-items-center rounded-lg text-slate-300 hover:bg-slate-800 lg:hidden"
        aria-label={t('shell.openMenu')}
        onclick={() => (drawer = true)}><Icon name="menu" size={20} /></button
      >
      <a href="/" class="lg:hidden" aria-label={t('shell.sorya')}><Logo size={22} wordmark={false} /></a>
      <!-- Home has its own big search. -->
      {#if page.url.pathname !== '/'}<SearchBox />{/if}
      <span class="flex-1"></span>
      <ProfileMenu />
    </header>
    <div class="min-h-0 flex-1 overflow-y-auto">
      {@render children()}
    </div>
  </div>
</div>
