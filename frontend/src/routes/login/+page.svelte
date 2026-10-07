<script lang="ts">
  import { goto } from '$app/navigation';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Field from '$lib/components/ui/Field.svelte';
  import { auth, login } from '$lib/stores/auth.svelte';

  let email = $state('');
  let password = $state('');
  let error = $state<unknown>(null);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    error = null;
    try {
      await login(email, password);
      await goto('/projects');
    } catch (e) {
      error = e;
    }
  }

  const input = 'w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm';
</script>

<main class="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-6">
  <div>
    <h1 class="text-2xl font-bold">Log in</h1>
    <p class="text-sm text-slate-400">AI Video Studio</p>
  </div>

  <form class="flex flex-col gap-4" onsubmit={submit}>
    <Field label="Email">
      <input bind:value={email} type="email" required autocomplete="email" class={input} />
    </Field>
    <Field label="Password">
      <input
        bind:value={password}
        type="password"
        required
        autocomplete="current-password"
        class={input}
      />
    </Field>
    <ErrorBanner {error} />
    <Button type="submit" loading={auth.loading}>Log in</Button>
  </form>

  <p class="text-sm text-slate-400">
    No account? <a href="/register" class="text-indigo-400 hover:text-indigo-300">Register</a>
  </p>
</main>
