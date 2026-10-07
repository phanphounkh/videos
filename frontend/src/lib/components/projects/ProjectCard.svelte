<script lang="ts">
  import Button from '$lib/components/ui/Button.svelte';
  import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
  import type { Project } from '$lib/types/api';

  let {
    project,
    onduplicate,
    ondelete
  }: {
    project: Project;
    onduplicate: (id: string) => void;
    ondelete: (id: string) => void;
  } = $props();

  const edited = $derived(new Date(project.updated_at).toLocaleString());
  const created = $derived(new Date(project.created_at).toLocaleDateString());
  const mmss = $derived(
    `${Math.floor(project.duration / 60)}:${String(Math.round(project.duration % 60)).padStart(2, '0')}`
  );
</script>

<article
  class="flex flex-col overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60 transition hover:border-slate-700"
>
  <a href={`/projects/${project.id}`} class="block">
    <div class="relative aspect-video w-full bg-slate-950">
      {#if project.thumbnail_url}
        <img
          src={project.thumbnail_url}
          alt=""
          class="h-full w-full object-cover"
          loading="lazy"
        />
      {:else}
        <div class="flex h-full w-full items-center justify-center text-xs text-slate-600">
          no thumbnail yet
        </div>
      {/if}
      <span class="absolute right-2 bottom-2 rounded bg-black/70 px-1.5 py-0.5 text-xs">
        {mmss}
      </span>
    </div>
  </a>

  <div class="flex flex-1 flex-col gap-2 p-4">
    <div class="flex items-start justify-between gap-2">
      <a href={`/projects/${project.id}`} class="font-semibold hover:text-indigo-300">
        {project.title}
      </a>
      <StatusBadge status={project.status} />
    </div>

    <p class="text-xs text-slate-500">
      {project.scene_count} scenes · {project.aspect_ratio} · {project.language}
    </p>
    <p class="text-xs text-slate-500">Created {created} · edited {edited}</p>

    <div class="mt-auto flex gap-2 pt-2">
      <Button variant="secondary" onclick={() => onduplicate(project.id)}>Duplicate</Button>
      <Button variant="ghost" onclick={() => ondelete(project.id)}>Delete</Button>
    </div>
  </div>
</article>
