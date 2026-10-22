<script lang="ts">
  import { goto } from '$app/navigation';
  import Logo from '$lib/components/ui/Logo.svelte';
  import { auth } from '$lib/stores/auth.svelte';

  // The landing page is just a router: signed in -> projects, otherwise login.
  $effect(() => {
    if (auth.ready) void goto(auth.user ? '/projects' : '/login', { replaceState: true });
  });
</script>

<main class="flex min-h-full items-center justify-center">
  <div class="animate-pulse"><Logo size={36} /></div>
</main>
