<script lang="ts">
  import { goto } from '$app/navigation';
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

  const input = 'w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm';
</script>

<main class="mx-auto flex min-h-screen max-w-sm flex-col justify-center gap-6 px-6">
  <div>
    <h1 class="text-2xl font-bold">Create an account</h1>
    <p class="text-sm text-slate-400">Khmer Story Studio</p>
  </div>

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
    <Button type="submit" loading={auth.loading}>Register</Button>
  </form>

  <p class="text-sm text-slate-400">
    Already registered? <a href="/login" class="text-indigo-400 hover:text-indigo-300">Log in</a>
  </p>
</main>
