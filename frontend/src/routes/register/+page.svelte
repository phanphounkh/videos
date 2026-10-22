<script lang="ts">
  import { goto } from '$app/navigation';
  import AuthShell from '$lib/components/auth/AuthShell.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Field from '$lib/components/ui/Field.svelte';
  import { auth, register } from '$lib/stores/auth.svelte';

  let email = $state('');
  let password = $state('');
  let fullName = $state('');
  let error = $state<unknown>(null);

  async function submit(event: SubmitEvent) {
    event.preventDefault();
    error = null;
    try {
      await register(email, password, fullName || undefined);
      await goto('/projects');
    } catch (e) {
      error = e;
    }
  }

  const input = 'h-10 w-full px-3 text-sm';
</script>

<AuthShell title="Create your account" subtitle="Start making videos in minutes.">
  <form class="flex flex-col gap-4" onsubmit={submit}>
    <Field label="Name">
      <input bind:value={fullName} class={input} autocomplete="name" />
    </Field>
    <Field label="Email">
      <input bind:value={email} type="email" required autocomplete="email" class={input} />
    </Field>
    <Field label="Password" hint="At least 8 characters.">
      <input
        bind:value={password}
        type="password"
        required
        minlength="8"
        maxlength="72"
        autocomplete="new-password"
        class={input}
      />
    </Field>
    <ErrorBanner {error} />
    <Button type="submit" loading={auth.loading} class="mt-1 h-10">Create account</Button>
  </form>

  {#snippet footer()}
    Already registered?
    <a href="/login" class="font-medium text-sun-400 hover:text-sun-300">Log in</a>
  {/snippet}
</AuthShell>
