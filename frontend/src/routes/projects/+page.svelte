<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import ProjectCard from '$lib/components/projects/ProjectCard.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
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
    if (!confirm('Delete this project and all of its scenes?')) return;
    try {
      await api.deleteProject(id);
      projects = projects.filter((p) => p.id !== id);
    } catch (e) {
      error = e;
    }
  }
</script>

<main class="mx-auto flex max-w-7xl flex-col gap-6 px-6 py-8">
  <div class="flex items-center justify-between gap-4">
    <div>
      <h1 class="text-2xl font-bold">Projects</h1>
      <p class="text-sm text-slate-400">{projects.length} project(s)</p>
    </div>
    <Button onclick={() => goto('/create')}>New video</Button>
  </div>

  <ErrorBanner {error} />

  {#if loading}
    <p class="text-sm text-slate-500">Loading projects…</p>
  {:else if !projects.length}
    <div class="rounded-xl border border-dashed border-slate-800 p-10 text-center">
      <p class="mb-4 text-slate-400">No projects yet.</p>
      <Button onclick={() => goto('/create')}>Create your first video</Button>
    </div>
  {:else}
    <div class="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {#each projects as project (project.id)}
        <ProjectCard {project} onduplicate={duplicate} ondelete={remove} />
      {/each}
    </div>
  {/if}
</main>
