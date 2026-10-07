<script lang="ts">
  /**
   * The editor page: owns data loading and every mutation, and polls while
   * media generation or a render is in progress.
   */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import VideoEditor from '$lib/components/editor/VideoEditor.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import type { Project, RenderJob, Scene } from '$lib/types/api';

  const projectId = $derived(page.params.id as string);

  let project = $state<Project | null>(null);
  let scenes = $state<Scene[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let saveLabel = $state('Saved');
  let error = $state<unknown>(null);

  let renderJob = $state<RenderJob | null>(null);
  let renderBusy = $state(false);

  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let pollAttempts = $state(0);
  const MAX_POLLS = 80; // ~3.5 minutes at 2.5s

  async function load() {
    try {
      const detail = await api.getProjectDetail(projectId);
      project = detail.project;
      scenes = detail.scenes;
    } catch (e) {
      error = e;
    } finally {
      loading = false;
    }
  }

  $effect(() => {
    if (!auth.ready) return;
    if (!auth.user) {
      void goto('/login', { replaceState: true });
    } else if (loading) {
      void load();
    }
  });

  // While background media generation is in flight, keep refreshing so images
  // and narration appear as each job finishes.
  //
  // Polling must NOT key off project.status alone: generation sets "ready" as
  // soon as the script is written, and the per-scene media jobs finish later, so
  // a client watching only the status can stop before the media lands. We also
  // poll while any scene is still missing its image or audio, with an attempt
  // cap so a permanently failed scene cannot poll forever.
  const mediaPending = $derived(
    project?.status === 'generating' ||
      (scenes.length > 0 && scenes.some((scene) => !scene.image_url || !scene.audio_url))
  );

  $effect(() => {
    if (!mediaPending || pollAttempts >= MAX_POLLS) return;
    pollTimer = setTimeout(() => {
      pollAttempts += 1;
      void load();
    }, 2500);
    return () => pollTimer && clearTimeout(pollTimer);
  });

  // Poll the render job until it reaches a terminal state.
  $effect(() => {
    const job = renderJob;
    if (!job || ['completed', 'failed'].includes(job.status)) return;
    const timer = setTimeout(async () => {
      try {
        renderJob = await api.getRenderJob(job.id);
        if (renderJob.status === 'completed') await load();
      } catch (e) {
        error = e;
      }
    }, 2000);
    return () => clearTimeout(timer);
  });

  async function mutate<T>(action: () => Promise<T>, reload = true): Promise<void> {
    saving = true;
    error = null;
    try {
      await action();
      if (reload) await load();
      saveLabel = `Saved ${new Date().toLocaleTimeString()}`;
    } catch (e) {
      error = e;
    } finally {
      saving = false;
    }
  }

  const saveScene = (id: string, patch: Partial<Scene>) =>
    mutate(() => api.updateScene(id, patch));
  const deleteScene = (id: string) => mutate(() => api.deleteScene(id));
  const duplicateScene = (id: string) => mutate(() => api.duplicateScene(id));
  const addScene = () =>
    mutate(() =>
      api.createScene(projectId, {
        narration: '',
        on_screen_text: 'New scene',
        duration: 5,
        visual_prompt: 'clean abstract background, minimal, soft lighting'
      })
    );
  const reorder = (ids: string[]) => mutate(() => api.reorderScenes(projectId, ids));
  const regenerateImage = (id: string) => mutate(() => api.generateSceneImage(id));
  const regenerateVoice = (id: string) => mutate(() => api.generateSceneVoice(id));
  const upload = (id: string, file: File) => mutate(() => api.uploadAsset(projectId, file, id));
  const rename = (title: string) => mutate(() => api.updateProject(projectId, { title }));

  async function startRender() {
    renderBusy = true;
    error = null;
    try {
      const created = await api.startRender(projectId);
      renderJob = await api.getRenderJob(created.job_id);
    } catch (e) {
      error = e;
    } finally {
      renderBusy = false;
    }
  }
</script>

<main class="mx-auto max-w-[1600px] px-4 py-6">
  {#if loading}
    <p class="text-sm text-slate-500">Loading project…</p>
  {:else if !project}
    <ErrorBanner {error} />
    <a href="/projects" class="text-sm text-indigo-400">← Back to projects</a>
  {:else}
    {#if mediaPending && pollAttempts < MAX_POLLS}
      <p
        class="mb-4 rounded-lg border border-amber-900/60 bg-amber-950/40 px-4 py-2 text-sm text-amber-200"
      >
        Generating images and narration in the background… this view refreshes itself.
      </p>
    {/if}

    <VideoEditor
      {project}
      {scenes}
      {saving}
      {saveLabel}
      {error}
      {renderJob}
      {renderBusy}
      onsaveScene={saveScene}
      ondeleteScene={deleteScene}
      onduplicateScene={duplicateScene}
      onaddScene={addScene}
      onreorder={reorder}
      onregenerateImage={regenerateImage}
      onregenerateVoice={regenerateVoice}
      onupload={upload}
      onrename={rename}
      onstartRender={startRender}
    />
  {/if}
</main>
