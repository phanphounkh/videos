<script lang="ts">
  import '../app.css';
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { auth, restoreSession } from '$lib/stores/auth.svelte';

  let { children } = $props();

  $effect(() => {
    if (!auth.ready) void restoreSession();
  });
  // Everything except the sign-in page needs an administrator.
  $effect(() => {
    if (auth.ready && !auth.user && page.url.pathname !== '/login') {
      void goto('/login', { replaceState: true });
    }
  });
</script>

{#if auth.ready}
  {@render children()}
{:else}
  <div class="grid h-dvh place-items-center text-sm text-slate-400">Loading…</div>
{/if}
