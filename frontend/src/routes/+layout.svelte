<script lang="ts">
  import '../app.css';
  import { page } from '$app/state';
  import { auth, logout, restoreSession } from '$lib/stores/auth.svelte';

  let { children } = $props();

  // Restore the session once, on the client, before any page needs the user.
  $effect(() => {
    if (!auth.ready) void restoreSession();
  });

  const onAuthPage = $derived(
    page.url.pathname === '/login' || page.url.pathname === '/register'
  );
</script>

<div class="min-h-screen">
  {#if !onAuthPage}
    <nav
      class="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/80 px-6 py-3 backdrop-blur"
    >
      <div class="mx-auto flex max-w-7xl items-center gap-4">
        <a href="/projects" class="font-semibold">Khmer Story Studio</a>
        <a href="/projects" class="text-sm text-slate-400 hover:text-slate-200">Projects</a>
        <a href="/create" class="text-sm text-slate-400 hover:text-slate-200">Create</a>
        <div class="flex-1"></div>
        {#if auth.user}
          <span class="text-xs text-slate-500">{auth.user.email}</span>
          <button class="text-sm text-slate-400 hover:text-slate-200" onclick={() => logout()}>
            Log out
          </button>
        {:else if auth.ready}
          <a href="/login" class="text-sm text-indigo-400 hover:text-indigo-300">Log in</a>
        {/if}
      </div>
    </nav>
  {/if}

  {@render children()}
</div>
