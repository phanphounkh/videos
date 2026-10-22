<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import ProjectCard from '$lib/components/projects/ProjectCard.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import type { Project } from '$lib/types/api';

  let projects = $state<Project[]>([]);
  let loading = $state(true);
  let error = $state<unknown>(null);

  async function load() {
    loading = true;
    error = null;
    try {
      projects = (await api.listProjects()).items;
    } catch (e) {
      error = e;
    } finally {
      loading = false;
    }
  }

  // Redirect to login once we know there is no session; load otherwise.
  $effect(() => {
    if (!auth.ready) return;
    if (!auth.user) {
      void goto('/login', { replaceState: true });
    } else if (loading && !projects.length && !error) {
      void load();
    }
  });

  async function duplicate(id: string) {
    try {
      await api.duplicateProject(id);
      await load();
    } catch (e) {
      error = e;
    }
  }

  async function remove(id: string) {
    try {
      await api.deleteProject(id);
      projects = projects.filter((p) => p.id !== id);
    } catch (e) {
      error = e;
    }
  }
</script>

<main class="mx-auto flex max-w-7xl flex-col gap-7 px-4 py-8 sm:px-6">
  <div class="flex flex-wrap items-end justify-between gap-4">
    <div>
      <h1 class="text-[28px] leading-tight font-semibold tracking-tight text-slate-50">Projects</h1>
      <p class="mt-1 text-sm text-slate-400">
        {#if loading}
          Loading your videos…
        {:else}
          {projects.length} video{projects.length === 1 ? '' : 's'}
        {/if}
      </p>
    </div>
    <Button icon="plus" onclick={() => goto('/create')}>New video</Button>
  </div>

  <ErrorBanner {error} />

  {#if loading}
    <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
      {#each [0, 1, 2] as n (n)}
        <div class="surface animate-pulse overflow-hidden">
          <div class="aspect-video bg-slate-800/60"></div>
          <div class="flex flex-col gap-3 p-4">
            <div class="h-4 w-3/4 rounded bg-slate-800"></div>
            <div class="h-3 w-1/2 rounded bg-slate-800/70"></div>
            <div class="mt-3 h-3 w-1/3 rounded bg-slate-800/70"></div>
          </div>
        </div>
      {/each}
    </div>
  {:else if !projects.length && !error}
    <div
      class="relative overflow-hidden rounded-2xl border border-dashed border-slate-700 px-6 py-16 text-center"
    >
      <div
        class="pointer-events-none absolute top-0 left-1/2 h-64 w-96 -translate-x-1/2 -translate-y-1/2 rounded-full bg-sun-500/15 blur-3xl"
      ></div>
      <div class="relative flex flex-col items-center gap-4">
        <Logo size={44} wordmark={false} />
        <div>
          <h2 class="text-xl font-semibold text-slate-50">Make your first video</h2>
          <p class="mx-auto mt-1.5 max-w-sm text-sm leading-relaxed text-slate-400">
            Pick a purpose, describe it in a sentence, and Sorya writes the script, voice and
            captions for you.
          </p>
        </div>
        <Button icon="sparkles" onclick={() => goto('/create')}>Create your first video</Button>
      </div>
    </div>
  {:else}
    <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {#each projects as project (project.id)}
        <ProjectCard {project} onduplicate={duplicate} ondelete={remove} />
      {/each}
    </div>
  {/if}
</main>
