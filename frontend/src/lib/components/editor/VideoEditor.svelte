<script lang="ts">
  /**
   * The editor shell: top bar, scene list, preview, properties panel, timeline.
   *
   * It owns no business logic - every mutation is a callback the page provides,
   * which keeps this component about layout and local UI state only.
   */
  import ExportDialog from '$lib/components/editor/ExportDialog.svelte';
  import PropertiesPanel from '$lib/components/editor/PropertiesPanel.svelte';
  import SceneList from '$lib/components/editor/SceneList.svelte';
  import Timeline from '$lib/components/editor/Timeline.svelte';
  import VideoPreview from '$lib/components/editor/VideoPreview.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
  import type { Project, RenderJob, Scene } from '$lib/types/api';

  let {
    project,
    scenes,
    saving = false,
    saveLabel = 'Saved',
    error = null,
    renderJob = null,
    renderBusy = false,
    onsaveScene,
    ondeleteScene,
    onduplicateScene,
    onaddScene,
    onreorder,
    onregenerateVoice,
    onmakeKhmer,
    onrename,
    onstartRender
  }: {
    project: Project;
    scenes: Scene[];
    saving?: boolean;
    saveLabel?: string;
    error?: unknown;
    renderJob?: RenderJob | null;
    renderBusy?: boolean;
    onsaveScene: (id: string, patch: Partial<Scene>) => void;
    ondeleteScene: (id: string) => void;
    onduplicateScene: (id: string) => void;
    onaddScene: () => void;
    onreorder: (ids: string[]) => void;
    onregenerateVoice: (id: string) => void;
    onmakeKhmer: () => void;
    onrename: (title: string) => void;
    onstartRender: () => void;
  } = $props();

  let selectedId = $state<string | null>(null);
  let time = $state(0);
  let exportOpen = $state(false);

  // The title is an editable draft that follows the server value until the user
  // types; `$state(project.title)` alone would freeze at the first render.
  let titleDraft = $state('');
  let titleSource = $state('');
  $effect(() => {
    if (project.title !== titleSource) {
      titleSource = project.title;
      titleDraft = project.title;
    }
  });

  const selected = $derived(scenes.find((scene) => scene.id === selectedId) ?? null);

  $effect(() => {
    if (!selectedId && scenes.length) selectedId = scenes[0].id;
  });

  function seekToScene(id: string) {
    selectedId = id;
    const scene = scenes.find((s) => s.id === id);
    if (scene) time = scene.start_time + 0.05;
  }
</script>

<div class="flex flex-col gap-4">
  <!-- top bar -->
  <header
    class="flex flex-wrap items-center gap-3 rounded-xl border border-slate-800 bg-slate-900/60 px-4 py-3"
  >
    <a href="/projects" class="text-sm text-slate-400 hover:text-slate-200">← Projects</a>

    <input
      bind:value={titleDraft}
      onblur={() => titleDraft !== project.title && onrename(titleDraft)}
      class="min-w-0 flex-1 rounded-lg border border-transparent bg-transparent px-2 py-1 text-lg font-semibold hover:border-slate-700 focus:border-slate-600"
    />

    <StatusBadge status={project.status} />
    <span class="text-xs text-slate-500">{saving ? 'Saving…' : saveLabel}</span>
    <span class="text-xs text-slate-500">
      {project.width}×{project.height} · {project.fps}fps · {project.duration.toFixed(1)}s
    </span>

    {#if !project.language.startsWith('km')}
      <Button variant="secondary" onclick={onmakeKhmer} loading={saving}>
        Regenerate in Khmer
      </Button>
    {/if}
    <Button onclick={() => (exportOpen = true)}>Export</Button>
  </header>

  <ErrorBanner {error} />

  <!-- three-column workspace -->
  <div class="flex flex-col gap-4 lg:flex-row">
    <SceneList
      {scenes}
      {selectedId}
      onselect={seekToScene}
      {onreorder}
      onadd={onaddScene}
    />

    <div class="flex min-w-0 flex-1 flex-col gap-4">
      <VideoPreview
        {scenes}
        projectTitle={project.title}
        aspectRatio={project.aspect_ratio}
        language={project.language}
        bind:time
        bind:selectedId
      />
    </div>

    <PropertiesPanel
      scene={selected}
      busy={saving}
      onsave={onsaveScene}
      ondelete={ondeleteScene}
      onduplicate={onduplicateScene}
      {onregenerateVoice}
    />
  </div>

  <Timeline {scenes} bind:time bind:selectedId />
</div>

{#if exportOpen}
  <ExportDialog
    job={renderJob}
    busy={renderBusy}
    {error}
    onstart={onstartRender}
    onclose={() => (exportOpen = false)}
  />
{/if}
