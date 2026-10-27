<script lang="ts">
  import { goto } from '$app/navigation';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';
  import { auth, login } from '$lib/stores/auth.svelte';

  let email = $state('');
  let password = $state('');
  let error = $state<unknown>(null);

  $effect(() => {
    if (auth.user) void goto('/', { replaceState: true });
  });

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    error = null;
    try {
      await login(email.trim(), password);
      await goto('/', { replaceState: true });
    } catch (e) {
      error = e;
    }
  }
</script>

<svelte:head><title>Sign in · Sorya Admin</title></svelte:head>

<main class="grid min-h-dvh place-items-center px-4">
  <form
    onsubmit={submit}
    class="flex w-full max-w-sm flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/70 p-6"
  >
    <div class="flex items-center gap-2">
      <Logo size={28} />
      <span class="rounded-full bg-slate-800 px-2 py-0.5 text-xs font-semibold text-slate-300"
        >Admin</span
      >
    </div>
    <div>
      <h1 class="text-xl font-bold text-slate-50">Sign in to the admin panel</h1>
      <p class="mt-1 text-sm text-slate-400">Administrator accounts only.</p>
    </div>
    <ErrorBanner {error} />
    <label class="flex flex-col gap-1 text-sm text-slate-300">
      Email
      <input
        type="email"
        required
        autocomplete="username"
        bind:value={email}
        class="h-10 rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 focus:border-sun-400 focus:outline-none"
      />
    </label>
    <label class="flex flex-col gap-1 text-sm text-slate-300">
      Password
      <input
        type="password"
        required
        autocomplete="current-password"
        bind:value={password}
        class="h-10 rounded-lg border border-slate-700 bg-slate-950 px-3 text-slate-100 focus:border-sun-400 focus:outline-none"
      />
    </label>
    <Button type="submit" disabled={auth.loading}>{auth.loading ? 'Signing in…' : 'Sign in'}</Button>
  </form>
</main>
