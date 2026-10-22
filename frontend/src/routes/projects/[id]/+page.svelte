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
  import { History, takeSnapshot } from '$lib/editor/history.svelte';
  import type { Layer, MediaAsset, MusicSettings, Project, RenderJob, Scene } from '$lib/types/api';

  const projectId = $derived(page.params.id as string);

  let project = $state<Project | null>(null);
  let scenes = $state<Scene[]>([]);
  let loading = $state(true);
  let saving = $state(false);
  let saveLabel = $state('Saved');
  let error = $state<unknown>(null);

  let renderJob = $state<RenderJob | null>(null);
  let renderBusy = $state(false);

  let media = $state<MediaAsset[]>([]);
  const history = new History();

  let pollTimer: ReturnType<typeof setTimeout> | null = null;
  let pollAttempts = $state(0);
  const MAX_POLLS = 80; // ~3.5 minutes at 2.5s

  async function refreshMedia() {
    try {
      media = await api.listMedia(projectId);
    } catch {
      // The library is a convenience; the editor works without it.
    }
  }

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
      void refreshMedia();
    }
  });

  // While background narration generation is in flight, keep refreshing so
  // each Khmer voice appears as its job finishes.
  //
  // Polling must NOT key off project.status alone: generation sets "ready" as
  // soon as the script is written, and the per-scene media jobs finish later, so
  // a client watching only the status can stop before the media lands. We also
  // poll while any scene is still missing audio, with an attempt cap so a
  // permanently failed scene cannot poll forever.
  const mediaPending = $derived(
    project?.status === 'generating' ||
      // A scene with nothing to say (a picture, a clip) has no voice by design.
      (scenes.length > 0 && scenes.some((scene) => scene.narration.trim() !== '' && !scene.audio_url))
  );

  const notice = $derived(
    mediaPending && pollAttempts < MAX_POLLS ? 'Generating narration in the background. This view refreshes itself.' : null
  );

  $effect(() => {
    if (!mediaPending || pollAttempts >= MAX_POLLS) return;
    pollTimer = setTimeout(() => {
      pollAttempts += 1;
      // Never replace the screen while an edit is being saved: the reply would
      // be older than what the user just did.
      if (!saving) void load();
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

  /** Runs a change and refreshes the screen. Returns whether it succeeded. */
  async function mutate<T>(action: () => Promise<T>, reload = true): Promise<boolean> {
    saving = true;
    error = null;
    try {
      await action();
      if (reload) await load();
      saveLabel = `Saved ${new Date().toLocaleTimeString()}`;
      return true;
    } catch (e) {
      error = e;
      // A change shown early (optimistic) did not happen: show the truth again.
      if (reload) await load();
      return false;
    } finally {
      saving = false;
    }
  }

  // ------------------------------------------------------------------ edits
  /** Remember the timeline as it is now, so the next change can be undone. */
  function remember() {
    if (project) history.record(takeSnapshot(scenes, project));
  }

  /**
   * An undoable edit. Edits run one at a time, in the order they were made: each
   * one starts from the screen the previous one produced, so the snapshot taken
   * for undo is always the real "before", even when edits arrive in quick
   * succession (dragging, typing, keyboard repeat).
   */
  let tail: Promise<unknown> = Promise.resolve();
  function act<T>(action: () => Promise<T>, optimistic?: () => void): Promise<void> {
    const run = tail.then(async () => {
      remember();
      optimistic?.();
      // A change that failed leaves nothing to undo.
      if (!(await mutate(action))) history.discardLast();
    });
    tail = run.catch(() => undefined);
    return run;
  }

  /** Shows a change at once; the request that saves it follows. */
  function patchLocal(id: string, change: (scene: Scene) => Scene) {
    scenes = scenes.map((scene) => (scene.id === id ? change(scene) : scene));
  }

  const mergeSettings = (current: Record<string, unknown>, patch: Record<string, unknown>) => {
    const merged = { ...current };
    for (const [key, value] of Object.entries(patch)) {
      if (value === null) delete merged[key];
      else merged[key] = value;
    }
    return merged;
  };

  const saveScene = (id: string, patch: Partial<Scene>) => act(() => api.updateScene(id, patch));
  const deleteScene = (id: string) => act(() => api.deleteScene(id));
  const duplicateScene = (id: string) => act(() => api.duplicateScene(id));
  const addScene = () =>
    act(() =>
      api.createScene(projectId, {
        narration: '',
        on_screen_text: 'New scene',
        duration: 5
      })
    );
  const reorder = (ids: string[]) =>
    act(
      () => api.reorderScenes(projectId, ids),
      () => {
        // Show the new order immediately; the server's numbering replaces it.
        const rank = new Map(ids.map((id, index) => [id, index + 1]));
        scenes = [...scenes]
          .map((scene) => ({ ...scene, scene_number: rank.get(scene.id) ?? scene.scene_number }))
          .sort((a, b) => a.scene_number - b.scene_number);
      }
    );
  const resizeScene = (id: string, duration: number) =>
    act(
      () => api.updateScene(id, { duration }),
      () => patchLocal(id, (scene) => ({ ...scene, duration }))
    );
  const trimScene = (id: string, start: number, end: number) =>
    act(() => api.trimScene(id, start, end));
  const splitScene = (id: string, at: number) => act(() => api.splitScene(id, at));

  /** Change some of a scene's settings (volumes, trim, fit...). `null` removes a key. */
  const changeSettings = (id: string, patch: Record<string, unknown>) =>
    act(
      () => api.updateScene(id, { settings: patch }),
      () => patchLocal(id, (scene) => ({ ...scene, settings: mergeSettings(scene.settings, patch) }))
    );
  const changeLayers = (id: string, layers: Layer[]) => changeSettings(id, { layers });
  const changeCaptions = (
    id: string,
    captions: { text: string; start_time: number; end_time: number }[]
  ) => act(() => api.setCaptions(id, captions));
  const resetCaptions = (id: string) => act(() => api.resetCaptions(id));

  const useMedia = (sceneId: string, asset: MediaAsset) =>
    act(() =>
      api.updateScene(
        sceneId,
        asset.type === 'video'
          ? { video_asset_id: asset.id }
          : { image_asset_id: asset.id, video_asset_id: null }
      )
    );
  const clearMedia = (sceneId: string) =>
    act(() => api.updateScene(sceneId, { image_asset_id: null, video_asset_id: null }));
  const addMediaScene = (asset: MediaAsset, position: number) =>
    act(async () => {
      const length = asset.type === 'video' && asset.duration ? Math.min(asset.duration, 60) : 5;
      const created = await api.createScene(projectId, {
        narration: '',
        on_screen_text: null,
        duration: Math.max(1, Math.round(length * 10) / 10),
        scene_number: position
      });
      await api.updateScene(
        created.id,
        asset.type === 'video' ? { video_asset_id: asset.id } : { image_asset_id: asset.id }
      );
    });

  const uploadMedia = (file: File, sceneId: string | null) => {
    const send = async () => {
      saveLabel = `Uploading ${file.name}…`;
      await api.uploadMedia(projectId, file, sceneId);
      await refreshMedia();
    };
    // Only an upload that replaces a scene's picture changes the timeline; one
    // that just fills the library is nothing to undo.
    return sceneId ? act(send) : mutate(send).then(() => undefined);
  };

  const uploadMusic = (file: File) =>
    act(async () => {
      saveLabel = `Uploading ${file.name}…`;
      await api.uploadMusic(projectId, file);
    });
  const removeMusic = () => act(() => api.removeMusic(projectId));
  const changeMusic = (patch: Partial<MusicSettings>) =>
    act(
      () => api.updateProject(projectId, { music: { ...project!.music, ...patch } }),
      () => {
        if (project) project = { ...project, music: { ...project.music, ...patch } };
      }
    );

  // -------------------------------------------------------------- undo / redo
  function travel(kind: 'undo' | 'redo'): Promise<void> {
    const run = tail.then(async () => {
      if (!project) return;
      const current = takeSnapshot(scenes, project);
      const target = kind === 'undo' ? history.undo(current) : history.redo(current);
      if (!target) return;
      const ok = await mutate(async () => {
        await api.restoreTimeline(projectId, target);
      });
      if (ok) saveLabel = `${kind === 'undo' ? 'Undid' : 'Redid'} at ${new Date().toLocaleTimeString()}`;
      else history.rollback(kind, target);
    });
    tail = run.catch(() => undefined);
    return run;
  }

  const rename = (title: string) => mutate(() => api.updateProject(projectId, { title }));
  const setPresenter = (presenter: boolean) =>
    mutate(() => api.updateProject(projectId, { presenter }));
  const regenerateVoice = (id: string) => mutate(() => api.generateSceneVoice(id));

  const makeKhmer = () => {
    if (!project) return;
    pollAttempts = 0;
    return mutate(() =>
      api.generate(projectId, {
        prompt: project?.prompt || project?.title || 'មេរៀនអប់រំ',
        duration: Math.min(300, Math.max(10, project?.target_duration || 60)),
        language: 'km',
        style: project?.style || 'social_media',
        purpose: project?.purpose,
        presenter: project?.presenter,
        cta_text: project?.cta_text,
        aspect_ratio: project?.aspect_ratio,
        tone: project?.tone,
        audience: project?.audience,
        generate_media: true
      })
    );
  };

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

<!-- The editor is an app, not a page: it fills the space under the top bar. -->
<div class="h-full">
  {#if loading}
    <div class="flex h-full items-center justify-center gap-3 text-sm text-slate-400">
      <span class="h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-transparent"></span>
      Opening project…
    </div>
  {:else if !project}
    <div class="mx-auto flex max-w-md flex-col gap-4 px-6 py-16">
      <ErrorBanner {error} />
      <a href="/projects" class="text-sm font-medium text-sun-300 hover:text-sun-200">← Back to projects</a>
    </div>
  {:else}
    <VideoEditor
      {project}
      {scenes}
      {saving}
      {saveLabel}
      {error}
      {renderJob}
      {renderBusy}
      {media}
      {notice}
      canUndo={history.canUndo}
      canRedo={history.canRedo}
      onsaveScene={saveScene}
      ondeleteScene={deleteScene}
      onduplicateScene={duplicateScene}
      onaddScene={addScene}
      onreorder={reorder}
      onresize={resizeScene}
      ontrim={trimScene}
      onsplit={splitScene}
      onsettings={changeSettings}
      onlayers={changeLayers}
      oncaptions={changeCaptions}
      onresetcaptions={resetCaptions}
      onuploadMedia={uploadMedia}
      onclearmedia={clearMedia}
      onusemedia={useMedia}
      onaddmediascene={addMediaScene}
      onuploadMusic={uploadMusic}
      onremoveMusic={removeMusic}
      onmusic={changeMusic}
      onundo={() => travel('undo')}
      onredo={() => travel('redo')}
      onregenerateVoice={regenerateVoice}
      onmakeKhmer={makeKhmer}
      onrename={rename}
      onpresenter={setPresenter}
      onstartRender={startRender}
    />
  {/if}
</div>
