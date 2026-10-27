<script lang="ts">
  /** The admin panel's frame: a sidebar of sections, and who is signed in. */
  import { page } from '$app/state';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';
  import { auth, logout } from '$lib/stores/auth.svelte';

  let { children } = $props();

  const SECTIONS: { href: string; label: string; icon: IconName; exact?: boolean }[] = [
    { href: '/', label: 'Overview', icon: 'grid', exact: true },
    { href: '/events', label: 'Events', icon: 'layers' },
    { href: '/sessions', label: 'Sessions', icon: 'clock' },
    { href: '/users', label: 'Users', icon: 'user' },
    { href: '/llm', label: 'LLM usage', icon: 'sparkles' },
    { href: '/health', label: 'Health', icon: 'check' }
  ];
  const path = $derived(page.url.pathname);
  const active = (s: (typeof SECTIONS)[number]) =>
    s.exact ? path === s.href : path === s.href || path.startsWith(`${s.href}/`);
</script>

{#if auth.user}
  <div class="flex h-dvh">
    <aside
      class="hidden w-56 shrink-0 flex-col gap-1 border-r border-slate-800 bg-slate-950 p-3 md:flex"
    >
      <div class="mb-3 flex items-center gap-2 px-2 pt-1">
        <Logo size={24} />
        <span class="rounded-full bg-slate-800 px-2 py-0.5 text-[11px] font-semibold text-slate-300"
          >Admin</span
        >
      </div>
      <nav class="flex flex-col gap-0.5" aria-label="Sections">
        {#each SECTIONS as s (s.href)}
          <a
            href={s.href}
            aria-current={active(s) ? 'page' : undefined}
            class="flex h-9 items-center gap-2.5 rounded-lg px-3 text-sm font-medium transition {active(s)
              ? 'bg-slate-800 text-slate-50'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100'}"
          >
            <Icon name={s.icon} size={15} />{s.label}
          </a>
        {/each}
      </nav>
      <div class="flex-1"></div>
      <div class="rounded-lg border border-slate-800 p-2.5 text-xs">
        <p class="truncate font-medium text-slate-200" title={auth.user.email}>{auth.user.email}</p>
        <button
          type="button"
          class="mt-1.5 inline-flex items-center gap-1.5 text-slate-400 hover:text-slate-100"
          onclick={logout}><Icon name="logout" size={13} /> Sign out</button
        >
      </div>
    </aside>

    <div class="flex min-w-0 flex-1 flex-col">
      <!-- narrow screens: the sections become a scrolling row -->
      <nav
        class="flex gap-1 overflow-x-auto border-b border-slate-800 bg-slate-950 px-3 py-2 md:hidden"
        aria-label="Sections"
      >
        {#each SECTIONS as s (s.href)}
          <a
            href={s.href}
            aria-current={active(s) ? 'page' : undefined}
            class="shrink-0 rounded-full px-3 py-1.5 text-sm font-medium {active(s)
              ? 'bg-slate-800 text-slate-50'
              : 'text-slate-400'}">{s.label}</a
          >
        {/each}
      </nav>
      <main class="viz-root min-w-0 flex-1 overflow-y-auto">
        <div class="mx-auto flex max-w-[110rem] flex-col gap-4 px-4 py-5 sm:px-6">
          {@render children()}
        </div>
      </main>
    </div>
  </div>
{/if}
