<script lang="ts">
  import Button from '$lib/components/ui/Button.svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
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

  const purposes: Record<string, { icon: IconName; label: string }> = {
    story: { icon: 'book', label: 'Story' },
    product_demo: { icon: 'package', label: 'Product demo' },
    social_post: { icon: 'phone', label: 'Social post' },
    creator: { icon: 'video', label: 'Creator' },
    explainer: { icon: 'lightbulb', label: 'Explainer' }
  };
  const purpose = $derived(
    purposes[project.purpose] ?? { icon: 'film' as IconName, label: project.purpose }
  );

  const mmss = $derived(
    `${Math.floor(project.duration / 60)}:${String(Math.round(project.duration % 60)).padStart(2, '0')}`
  );

  /** "2h ago" for recent edits, the date once it is older than a week. */
  function ago(iso: string): string {
    const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
    if (seconds < 60) return 'just now';
    const units: [number, string][] = [
      [60, 'm'],
      [3600, 'h'],
      [86400, 'd']
    ];
    if (seconds < 7 * 86400) {
      const [size, unit] = [...units].reverse().find(([s]) => seconds >= s) ?? units[0];
      return `${Math.floor(seconds / size)}${unit} ago`;
    }
    return new Date(iso).toLocaleDateString();
  }
  const edited = $derived(ago(project.updated_at));

  let confirming = $state(false);
</script>

<article
  class="group surface flex flex-col overflow-hidden transition hover:-translate-y-0.5 hover:border-slate-700 hover:shadow-pop"
>
  <a href={`/projects/${project.id}`} class="relative block" aria-label={`Open ${project.title}`}>
    <div class="relative aspect-video w-full overflow-hidden bg-slate-950">
      {#if project.thumbnail_url}
        <img
          src={project.thumbnail_url}
          alt=""
          class="h-full w-full object-contain transition duration-300 group-hover:scale-[1.02]"
          loading="lazy"
        />
      {:else}
        <div
          class="flex h-full w-full flex-col items-center justify-center gap-2 bg-gradient-to-br from-slate-900 to-slate-950 text-slate-600"
        >
          <Icon name={purpose.icon} size={28} />
          <span class="text-xs">No thumbnail yet</span>
        </div>
      {/if}
      <div
        class="pointer-events-none absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-slate-950/80 to-transparent"
      ></div>
      <span
        class="absolute top-2.5 left-2.5 inline-flex items-center gap-1.5 rounded-full bg-slate-950/75 px-2.5 py-1 text-xs font-medium text-slate-200 backdrop-blur"
      >
        <Icon name={purpose.icon} size={12} class="text-sun-300" />
        {purpose.label}
      </span>
      <span
        class="absolute right-2.5 bottom-2.5 rounded-md bg-slate-950/80 px-1.5 py-0.5 font-mono text-xs text-slate-100"
      >
        {mmss}
      </span>
    </div>
  </a>

  <div class="flex flex-1 flex-col gap-3 p-4">
    <div class="flex items-start justify-between gap-3">
      <a
        href={`/projects/${project.id}`}
        class="line-clamp-2 text-base leading-snug font-semibold text-slate-50 hover:text-sun-300"
        style="line-height:1.55"
      >
        {project.title}
      </a>
      <StatusBadge status={project.status} />
    </div>

    <p class="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
      <span>{project.scene_count} scenes</span>
      <span class="text-slate-700">·</span>
      <span>{project.aspect_ratio}</span>
      <span class="text-slate-700">·</span>
      <span class="uppercase">{project.language}</span>
    </p>

    <div class="mt-auto flex items-center justify-between gap-2 pt-1">
      <span class="inline-flex items-center gap-1.5 text-xs text-slate-500">
        <Icon name="clock" size={12} />
        Edited {edited}
      </span>

      {#if confirming}
        <div class="flex items-center gap-1.5">
          <span class="text-xs text-slate-300">Delete?</span>
          <Button variant="danger" size="sm" onclick={() => ondelete(project.id)}>Yes</Button>
          <Button variant="ghost" size="sm" onclick={() => (confirming = false)}>No</Button>
        </div>
      {:else}
        <div
          class="flex items-center gap-0.5 transition sm:opacity-0 sm:group-focus-within:opacity-100 sm:group-hover:opacity-100"
        >
          <button
            class="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
            title="Duplicate"
            aria-label="Duplicate project"
            onclick={() => onduplicate(project.id)}
          >
            <Icon name="copy" size={15} />
          </button>
          <button
            class="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-red-500/15 hover:text-red-300"
            title="Delete"
            aria-label="Delete project"
            onclick={() => (confirming = true)}
          >
            <Icon name="trash" size={15} />
          </button>
        </div>
      {/if}
    </div>
  </div>
</article>
