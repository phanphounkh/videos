<script lang="ts">
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';

  // The landing page is just a router: signed in -> projects, otherwise login.
  $effect(() => {
    if (auth.ready) void goto(auth.user ? '/projects' : '/login', { replaceState: true });
  });
</script>

<main class="flex min-h-[60vh] items-center justify-center">
  <p class="text-sm text-slate-500">Loading…</p>
</main>
