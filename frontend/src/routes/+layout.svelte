<script lang="ts">
  import '../app.css';
  import { afterNavigate } from '$app/navigation';
  import { page } from '$app/state';
  import AppShell from '$lib/components/shell/AppShell.svelte';
  import { initLocale } from '$lib/i18n/index.svelte';
  import { auth, restoreSession } from '$lib/stores/auth.svelte';
  import { pageView, startTelemetry } from '$lib/telemetry/client';

  let { children } = $props();

  // The saved language (or the browser's) once the page is in the browser.
  $effect(() => {
    initLocale();
  });

  // Restore the session once, on the client, before any page needs the user.
  $effect(() => {
    if (!auth.ready) void restoreSession();
  });

  // Browser telemetry starts straight away, signed in or not: the login page and early
  // errors are worth seeing too. The service attributes events to a user only when a
  // valid token comes with them.
  $effect(() => {
    startTelemetry();
  });
  // One page_view per navigation, including the first load.
  afterNavigate(() => pageView());

  const path = $derived(page.url.pathname);
  const onAuthPage = $derived(path === '/login' || path === '/register');
  // The editor has its own full-screen chrome; the app shell would only steal space.
  const inEditor = $derived(/^\/projects\/[^/]+$/.test(path));
  // Signed-out visitors only ever see the sign-in pages, so no shell for them either.
  const framed = $derived(!onAuthPage && !inEditor && !!auth.user);
</script>

{#if framed}
  <AppShell>{@render children()}</AppShell>
{:else}
  <div class="h-dvh overflow-y-auto">
    {@render children()}
  </div>
{/if}
