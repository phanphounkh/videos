<script lang="ts">
  import { goto } from '$app/navigation';
  import AuthShell from '$lib/components/auth/AuthShell.svelte';
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

  const input = 'h-10 w-full px-3 text-sm';
</script>

<AuthShell title="Welcome back" subtitle="Log in to keep editing your videos.">
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
    <Button type="submit" loading={auth.loading} class="mt-1 h-10">Log in</Button>
  </form>

  {#snippet footer()}
    No account yet?
    <a href="/register" class="font-medium text-sun-400 hover:text-sun-300">Create one</a>
  {/snippet}
</AuthShell>
