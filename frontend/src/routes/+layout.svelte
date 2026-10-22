<script lang="ts">
  import '../app.css';
  import { page } from '$app/state';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';
  import { auth, logout, restoreSession } from '$lib/stores/auth.svelte';

  let { children } = $props();

  // Restore the session once, on the client, before any page needs the user.
  $effect(() => {
    if (!auth.ready) void restoreSession();
  });

  const path = $derived(page.url.pathname);
  const onAuthPage = $derived(path === '/login' || path === '/register');

  const links = [
    { href: '/projects', label: 'Projects', icon: 'grid' as const },
    { href: '/create', label: 'Create', icon: 'sparkles' as const }
  ];
  // /projects stays active inside an open project (the editor).
  const active = (href: string) => path === href || path.startsWith(`${href}/`);
</script>

<div class="flex h-dvh flex-col">
  {#if !onAuthPage}
    <header
      class="z-40 flex h-12 shrink-0 items-center gap-2 border-b border-slate-800 bg-slate-950/80 px-3 backdrop-blur sm:gap-4 sm:px-5"
    >
      <a href="/projects" class="mr-1 rounded-md" aria-label="Sorya home"><Logo size={24} /></a>
      <nav class="flex items-center gap-1" aria-label="Main">
        {#each links as link (link.href)}
          <a
            href={link.href}
            aria-current={active(link.href) ? 'page' : undefined}
            class="inline-flex h-8 items-center gap-1.5 rounded-full px-3 text-sm font-medium transition {active(
              link.href
            )
              ? 'bg-slate-800 text-slate-50'
              : 'text-slate-400 hover:bg-slate-900 hover:text-slate-100'}"
          >
            <Icon name={link.icon} size={14} />
            <span class="hidden sm:inline">{link.label}</span>
            <span class="sm:hidden">{link.label}</span>
          </a>
        {/each}
      </nav>

      <div class="flex-1"></div>

      {#if auth.user}
        <span
          class="hidden max-w-56 items-center gap-2 truncate rounded-full border border-slate-800 bg-slate-900 py-1 pr-3 pl-1 text-xs text-slate-300 md:inline-flex"
          title={auth.user.email}
        >
          <span
            class="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-[image:var(--sun-gradient)] text-[11px] font-bold text-sun-950"
            >{auth.user.email.slice(0, 1).toUpperCase()}</span
          >
          <span class="truncate">{auth.user.email}</span>
        </span>
        <button
          class="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
          title="Log out"
          aria-label="Log out"
          onclick={() => logout()}
        >
          <Icon name="logout" size={16} />
        </button>
      {:else if auth.ready}
        <a href="/login" class="text-sm font-medium text-sun-400 hover:text-sun-300">Log in</a>
      {/if}
    </header>
  {/if}

  <!-- The editor fills this area and scrolls its own panels; other pages scroll here. -->
  <div class="min-h-0 flex-1 overflow-y-auto">
    {@render children()}
  </div>
</div>
