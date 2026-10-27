<script lang="ts">
  /**
   * The editor shell: top bar, tool rail + panel (scenes, media, text, elements,
   * audio, captions), preview, properties panel, toolbar and timeline, plus the
   * keyboard shortcuts.
   *
   * It owns no business logic - every change is a callback the page provides.
   * What it does own is local UI state (selection, playhead, zoom, tabs) and the
   * small decisions that turn "the playhead is here" into "split this scene at
   * 3.2s".
   *
   * Shortcuts: Space play/pause · S split at the playhead · Delete remove the
   * selected text/sticker or scene · Ctrl+Z undo · Ctrl+Shift+Z / Ctrl+Y redo ·
   * Ctrl+D duplicate · ←/→ one frame (Shift: one second) · Home/End · +/- zoom ·
   * Esc deselect.
   */
  import { untrack } from 'svelte';
  import AudioPanel from '$lib/components/editor/AudioPanel.svelte';
  import CaptionEditor from '$lib/components/editor/CaptionEditor.svelte';
  import EditorToolbar from '$lib/components/editor/EditorToolbar.svelte';
  import ExportDialog from '$lib/components/editor/ExportDialog.svelte';
  import ElementsPanel from '$lib/components/editor/ElementsPanel.svelte';
  import MediaLibrary from '$lib/components/editor/MediaLibrary.svelte';
  import PropertiesPanel from '$lib/components/editor/PropertiesPanel.svelte';
  import SceneList from '$lib/components/editor/SceneList.svelte';
  import TextPanel from '$lib/components/editor/TextPanel.svelte';
  import Timeline from '$lib/components/editor/Timeline.svelte';
  import ToolRail, { type Tool } from '$lib/components/editor/ToolRail.svelte';
  import VideoPreview from '$lib/components/editor/VideoPreview.svelte';
  import AvatarImage from '$lib/components/avatars/AvatarImage.svelte';
  import AvatarPicker from '$lib/components/avatars/AvatarPicker.svelte';
  import { hostInfo, loadHosts } from '$lib/components/avatars/hosts.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
  import ProfileMenu from '$lib/components/account/ProfileMenu.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Logo from '$lib/components/ui/Logo.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
  import { clamp, layersOf, makeLayer, newId, round } from '$lib/editor/layers';
  import { t } from '$lib/i18n/index.svelte';
  import type {
    Layer,
    MediaAsset,
    MusicSettings,
    Project,
    RenderJob,
    Scene
  } from '$lib/types/api';

  let {
    project,
    scenes,
    media = [],
    saving = false,
    saveLabel = '',
    error = null,
    notice = null,
    canUndo = false,
    canRedo = false,
    renderJob = null,
    renderBusy = false,
    onsaveScene,
    ondeleteScene,
    onduplicateScene,
    onaddScene,
    onreorder,
    onresize,
    ontrim,
    onsplit,
    onsettings,
    onlayers,
    oncaptions,
    onresetcaptions,
    onuploadMedia,
    onclearmedia,
    onusemedia,
    onaddmediascene,
    onuploadMusic,
    onremoveMusic,
    onmusic,
    onundo,
    onredo,
    onregenerateVoice,
    onmakeKhmer,
    onrename,
    onpresenter,
    onaspect,
    onavatar,
    onstartRender
  }: {
    project: Project;
    scenes: Scene[];
    media?: MediaAsset[];
    saving?: boolean;
    saveLabel?: string;
    error?: unknown;
    notice?: string | null;
    canUndo?: boolean;
    canRedo?: boolean;
    renderJob?: RenderJob | null;
    renderBusy?: boolean;
    onsaveScene: (id: string, patch: Partial<Scene>) => void;
    ondeleteScene: (id: string) => void;
    onduplicateScene: (id: string) => void;
    onaddScene: () => void;
    onreorder: (ids: string[]) => void;
    onresize: (id: string, duration: number) => void;
    ontrim: (id: string, start: number, end: number) => void;
    onsplit: (id: string, at: number) => void;
    onsettings: (sceneId: string, patch: Record<string, unknown>) => void;
    onlayers: (sceneId: string, layers: Layer[]) => void;
    oncaptions: (
      sceneId: string,
      captions: { text: string; start_time: number; end_time: number }[]
    ) => void;
    onresetcaptions: (sceneId: string) => void;
    onuploadMedia: (file: File, sceneId: string | null) => void;
    onclearmedia: (sceneId: string) => void;
    onusemedia: (sceneId: string, asset: MediaAsset) => void;
    onaddmediascene: (asset: MediaAsset, position: number) => void;
    onuploadMusic: (file: File) => void;
    onremoveMusic: () => void;
    onmusic: (patch: Partial<MusicSettings>) => void;
    onundo: () => void;
    onredo: () => void;
    onregenerateVoice: (id: string) => void;
    onmakeKhmer: () => void;
    onrename: (title: string) => void;
    onpresenter: (on: boolean) => void;
    onaspect: (ratio: string) => void;
    onavatar: (avatar: string | null) => void;
    onstartRender: () => void;
  } = $props();


  // ---------------------------------------------------------------- UI state
  let selectedId = $state<string | null>(null);
  let selectedLayerId = $state<string | null>(null);
  let time = $state(0);
  let playing = $state(false);
  let tool = $state<Tool>('scenes');
  let zoom = $state<number | null>(null);
  let pps = $state(40);
  let textfocus = $state(0);
  let exportOpen = $state(false);
  let preview = $state<{ toggle: () => void }>();
  // Per-track toggles. Editor-local on purpose: never saved, never exported.
  // Lock stops edits on a track; hidden / muted only change the preview.
  type Track = 'title' | 'video' | 'voice' | 'captions' | 'music';
  const flags = (): Record<Track, boolean> => ({
    title: false,
    video: false,
    voice: false,
    captions: false,
    music: false
  });
  let hint = $state<string | null>(null);
  let locked = $state(flags());
  let hidden = $state(flags());
  let muted = $state(flags());
  function toggleTrack(track: string, flag: 'locked' | 'hidden' | 'muted') {
    const bag = flag === 'locked' ? locked : flag === 'hidden' ? hidden : muted;
    bag[track as Track] = !bag[track as Track];
  }

  // Height of the timeline panel, remembered between visits.
  const HEIGHT_KEY = 'sorya.timelineHeight';
  const readHeight = (): number => {
    try {
      const saved = Number(localStorage.getItem(HEIGHT_KEY));
      if (Number.isFinite(saved) && saved >= 180) return saved;
    } catch {
      // fall through to the default
    }
    // About a third of the window: the stage stays the biggest thing on screen.
    return clamp(Math.round(window.innerHeight * 0.36), 230, 340);
  };
  let timelineHeight = $state(readHeight());

  function startResize(event: PointerEvent) {
    event.preventDefault();
    const startY = event.clientY;
    const startHeight = timelineHeight;
    const move = (e: PointerEvent) => {
      const limit = Math.round(window.innerHeight * 0.7);
      timelineHeight = clamp(startHeight + (startY - e.clientY), 180, limit);
    };
    const stop = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', stop);
      try {
        localStorage.setItem(HEIGHT_KEY, String(Math.round(timelineHeight)));
      } catch {
        // Remembering the height is a convenience only.
      }
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop);
  }
  let hintTimer: ReturnType<typeof setTimeout> | undefined;

  /** A short message for something the user tried that cannot work yet. */
  function tell(message: string) {
    hint = message;
    clearTimeout(hintTimer);
    hintTimer = setTimeout(() => (hint = null), 4500);
  }

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

  // ------------------------------------------------------------- derived facts
  const ordered = $derived([...scenes].sort((a, b) => a.scene_number - b.scene_number));
  const total = $derived(ordered.reduce((sum, scene) => sum + scene.duration, 0));
  const frame = $derived(1 / Math.max(1, project.fps));
  const selected = $derived(scenes.find((scene) => scene.id === selectedId) ?? null);

  const startOf = (id: string): number => {
    let cursor = 0;
    for (const scene of ordered) {
      if (scene.id === id) return cursor;
      cursor += scene.duration;
    }
    return 0;
  };

  /** The scene under the playhead, and how far into it the playhead is. */
  const underPlayhead = $derived.by(() => {
    let cursor = 0;
    for (const scene of ordered) {
      if (time < cursor + scene.duration) return { scene, at: time - cursor };
      cursor += scene.duration;
    }
    const last = ordered.at(-1);
    return last ? { scene: last, at: last.duration } : null;
  });

  $effect(() => {
    if (!selectedId && scenes.length) selectedId = scenes[0].id;
    else if (selectedId && !selected) selectedId = scenes[0]?.id ?? null;
  });
  // A selected layer that no longer exists (undo, delete, another scene) is dropped.
  // This must react to the SCENES changing, not to the selection changing: a layer
  // is selected a moment before the scene data that contains it arrives.
  $effect(() => {
    void scenes;
    untrack(() => {
      if (selectedLayerId && !(selected && layersOf(selected).some((l) => l.id === selectedLayerId))) {
        selectedLayerId = null;
      }
    });
  });

  // ---------------------------------------------------------------- actions
  function seekToScene(id: string) {
    selectedId = id;
    selectedLayerId = null;
    time = startOf(id) + 0.05;
  }

  function split() {
    const here = underPlayhead;
    if (!here) return tell(t('editor.hint.nothingToSplit'));
    const { scene, at } = here;
    if (at < 0.2 || scene.duration - at < 0.2) {
      return tell(t('editor.hint.splitInside'));
    }
    selectedId = scene.id;
    onsplit(scene.id, round(at, 3));
  }

  function deleteSelected() {
    if (selected && selectedLayerId) {
      onlayers(selected.id, layersOf(selected).filter((l) => l.id !== selectedLayerId));
      selectedLayerId = null;
    } else if (selected) {
      ondeleteScene(selected.id);
    }
  }

  function duplicateSelected() {
    if (selected && selectedLayerId) {
      const layers = layersOf(selected);
      const source = layers.find((l) => l.id === selectedLayerId);
      if (!source) return;
      const copy = { ...source, id: newId(), x: Math.min(95, source.x + 5), y: Math.min(95, source.y + 5) };
      selectedLayerId = copy.id;
      onlayers(selected.id, [...layers, copy]);
    } else if (selected) {
      onduplicateScene(selected.id);
    }
  }

  /** New text or sticker on the scene under the playhead. */
  function addLayer(kind: 'text' | 'sticker', patch: Partial<Layer> = {}) {
    const here = underPlayhead;
    if (!here) return tell(t('editor.hint.addScene'));
    const layer = { ...makeLayer(kind, here.scene, here.at, project.language), ...patch };
    selectedId = here.scene.id;
    selectedLayerId = layer.id;
    onlayers(here.scene.id, [...layersOf(here.scene), layer]);
  }

  function patchLayer(sceneId: string, layerId: string, patch: Partial<Layer>) {
    const scene = scenes.find((s) => s.id === sceneId);
    if (!scene) return;
    onlayers(
      sceneId,
      layersOf(scene).map((layer) => (layer.id === layerId ? { ...layer, ...patch } : layer))
    );
  }

  function uploadToScene(file: File, sceneId: string | null) {
    if (!sceneId) return tell(t('editor.hint.selectOrMedia'));
    onuploadMedia(file, sceneId);
  }

  /** New scene from library media, right after the scene under the playhead. */
  function addMediaScene(asset: MediaAsset) {
    const after = underPlayhead?.scene.scene_number ?? ordered.length;
    onaddmediascene(asset, after + 1);
  }

  function zoomBy(factor: number) {
    zoom = clamp(pps * factor, 2, 600);
  }

  // ---------------------------------------------------------------- keyboard
  function onkeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null;
    if (
      target &&
      (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
    ) {
      return;
    }
    if (exportOpen) return;

    const modifier = event.ctrlKey || event.metaKey;
    const key = event.key.toLowerCase();

    if (modifier && key === 'z') {
      event.preventDefault();
      if (event.shiftKey) onredo();
      else onundo();
      return;
    }
    if (modifier && key === 'y') {
      event.preventDefault();
      onredo();
      return;
    }
    if (modifier && key === 'd') {
      event.preventDefault();
      duplicateSelected();
      return;
    }
    if (modifier || event.altKey) return;

    switch (event.key) {
      case ' ':
        event.preventDefault();
        // A focused button would also "click" on Space; let go of it first.
        if (target?.tagName === 'BUTTON') target.blur();
        preview?.toggle();
        break;
      case 's':
      case 'S':
        event.preventDefault();
        split();
        break;
      case 'Delete':
      case 'Backspace':
        event.preventDefault();
        deleteSelected();
        break;
      case 'ArrowLeft':
        event.preventDefault();
        time = clamp(time - (event.shiftKey ? 1 : frame), 0, total);
        break;
      case 'ArrowRight':
        event.preventDefault();
        time = clamp(time + (event.shiftKey ? 1 : frame), 0, total);
        break;
      case 'Home':
        event.preventDefault();
        time = 0;
        break;
      case 'End':
        event.preventDefault();
        time = total;
        break;
      case '+':
      case '=':
        zoomBy(1.4);
        break;
      case '-':
        zoomBy(1 / 1.4);
        break;
      case 'Escape':
        selectedLayerId = null;
        break;
    }
  }
  // ---- host ("avatar") picker in the header
  let choosingHost = $state(false);
  const hostLabel = $derived(hostInfo(project.avatar_resolved)?.name ?? '');
  $effect(() => {
    if (project.presenter) void loadHosts();
  });
</script>

<svelte:window {onkeydown} />

<div class="flex h-full min-h-0 flex-col overflow-y-auto bg-slate-950 lg:overflow-hidden">
  <!-- project bar -->
  <header class="flex h-14 shrink-0 items-center gap-2 border-b border-slate-800 bg-slate-900 px-3">
    <a
      href="/projects"
      class="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
      title={t('editor.top.back')}
      aria-label={t('editor.top.back')}
    >
      <Icon name="arrowLeft" size={17} />
    </a>
    <a href="/" class="rounded-md" aria-label={t('editor.top.home')} title={t('editor.top.homeTip')}><Logo size={24} wordmark={false} /></a>

    <label class="relative ml-1 flex min-w-0 max-w-xs flex-1 items-center">
      <input
        bind:value={titleDraft}
        onblur={() => titleDraft !== project.title && onrename(titleDraft)}
        onkeydown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
        class="!h-9 w-full min-w-0 !border-transparent !bg-transparent !pr-8 px-2 text-[15px] font-semibold text-slate-50 hover:!border-slate-700 focus:!bg-slate-950"
        aria-label={t('editor.top.titleLabel')}
      />
      <Icon name="pencil" size={13} class="pointer-events-none absolute right-2.5 text-slate-500" />
    </label>

    <span class="hidden items-center gap-3 text-xs text-slate-500 md:flex">
      {#if notice}
        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-sun-400/10 px-2.5 py-1 text-xs font-medium text-sun-200"
          title={notice}
          role="status"
        >
          <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-sun-400"></span>
          {t('editor.top.generating')}
        </span>
      {:else}
        <StatusBadge status={project.status} />
      {/if}
      <span class="inline-flex items-center gap-1.5">
        {#if saving}
          <span class="h-3 w-3 animate-spin rounded-full border-2 border-slate-500 border-t-transparent"></span>
          {t('editor.top.saving')}
        {:else}
          <Icon name="check" size={13} class="text-emerald-400" />
          {saveLabel || t('editor.top.allSaved')}
        {/if}
      </span>
    </span>

    <span class="flex-1"></span>

    <label
      class="hidden cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 lg:flex"
      title={t('editor.top.hostTip')}
    >
      <input
        type="checkbox"
        checked={project.presenter}
        onchange={(e) => onpresenter(e.currentTarget.checked)}
      />
      {t('editor.top.host')}
    </label>
    {#if project.presenter}
      <button
        type="button"
        class="hidden max-w-40 items-center gap-2 rounded-lg py-1 pr-2.5 pl-1 text-xs font-medium text-slate-200 hover:bg-slate-800 lg:flex"
        title={t('avatars.editor.change')}
        aria-label="{t('avatars.editor.change')}: {hostLabel}"
        onclick={() => (choosingHost = true)}
      >
        <AvatarImage src={hostInfo(project.avatar_resolved)?.image} name={hostLabel || '?'} fit={hostInfo(project.avatar_resolved)?.custom ? 'cover' : 'contain'} class="h-7 w-6 shrink-0 rounded-md bg-slate-950 [&_span]:text-sm" />
        <span class="truncate">{hostLabel}{#if project.avatar === null} · {t('avatars.editor.automaticSuffix')}{/if}</span>
      </button>
    {/if}

    {#if !project.language.startsWith('km')}
      <span class="hidden lg:inline">
        <Button variant="secondary" size="sm" onclick={onmakeKhmer} loading={saving}>
          {t('editor.top.khmer')}
        </Button>
      </span>
    {/if}

    <div class="flex items-center gap-0.5">
      <button
        class="grid h-9 w-9 place-items-center rounded-lg text-slate-300 transition hover:bg-slate-800 disabled:opacity-35 disabled:hover:bg-transparent"
        disabled={!canUndo}
        onclick={onundo}
        title={t('editor.top.undoTip')}
        aria-label={t('editor.top.undo')}><Icon name="undo" size={17} /></button
      >
      <button
        class="grid h-9 w-9 place-items-center rounded-lg text-slate-300 transition hover:bg-slate-800 disabled:opacity-35 disabled:hover:bg-transparent"
        disabled={!canRedo}
        onclick={onredo}
        title={t('editor.top.redoTip')}
        aria-label={t('editor.top.redo')}><Icon name="redo" size={17} /></button
      >
    </div>

    <Button icon="download" onclick={() => (exportOpen = true)}>{t('editor.top.export')}</Button>
    <ProfileMenu />
  </header>

  {#if error}
    <div class="shrink-0 border-b border-slate-800 bg-slate-900/60 px-3 py-2">
      <ErrorBanner {error} />
    </div>
  {/if}

  <!-- workspace: tool rail + panel | stage | properties -->
  <div class="relative flex min-h-[28rem] flex-col lg:min-h-0 lg:flex-1 lg:flex-row">
    <!-- a quiet toast over the stage, so messages never push the video around -->
    {#if hint}
      <p
        class="pointer-events-none absolute top-3 left-1/2 z-30 flex max-w-[90%] -translate-x-1/2 items-center gap-2 rounded-full border border-sun-400/30 bg-slate-900/95 px-4 py-2 text-sm text-sun-100 shadow-pop backdrop-blur"
        role="status"
      >
        <Icon name="sparkles" size={15} class="shrink-0 text-sun-300" />
        {hint}
      </p>
    {/if}

    <ToolRail bind:tool />

    <aside
      class="flex max-h-80 w-full shrink-0 flex-col border-b border-slate-800 bg-slate-900/40 lg:max-h-none lg:w-[19rem] lg:border-r lg:border-b-0"
    >
      <div class="flex h-12 shrink-0 items-center border-b border-slate-800 px-4">
        <h2 class="text-sm font-semibold text-slate-50">{t(`editor.tool.${tool}`)}</h2>
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto p-3">
        {#if tool === 'scenes'}
          <SceneList {scenes} {selectedId} onselect={seekToScene} {onreorder} onadd={onaddScene} />
        {:else if tool === 'media'}
          <MediaLibrary
            {media}
            hasScene={!!selected}
            onupload={(file) => onuploadMedia(file, null)}
            onuse={(asset) => selected && onusemedia(selected.id, asset)}
            onaddscene={addMediaScene}
          />
        {:else if tool === 'text'}
          <TextPanel
            {scenes}
            {selectedLayerId}
            onadd={(patch) => addLayer('text', patch)}
            onselect={(sceneId, layerId) => {
              selectedId = sceneId;
              selectedLayerId = layerId;
              time = startOf(sceneId) + (layersOf(scenes.find((s) => s.id === sceneId)!).find((l) => l.id === layerId)?.start ?? 0) + 0.05;
            }}
          />
        {:else if tool === 'elements'}
          <ElementsPanel onadd={(emoji) => addLayer('sticker', { text: emoji })} />
        {:else if tool === 'audio'}
          <AudioPanel
            scene={selected}
            {project}
            busy={saving}
            {onsettings}
            {onuploadMusic}
            {onremoveMusic}
            {onmusic}
          />
        {:else if selected}
          <CaptionEditor
            scene={selected}
            at={underPlayhead?.scene.id === selected.id ? underPlayhead.at : -1}
            oncommit={(captions) => oncaptions(selected.id, captions)}
            onreset={() => onresetcaptions(selected.id)}
            onseek={(seconds) => (time = clamp(startOf(selected.id) + seconds, 0, total))}
          />
        {:else}
          <p class="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-500">
            {t('editor.cap.selectScene')}
          </p>
        {/if}
      </div>
    </aside>

    <main class="h-[26rem] min-w-0 flex-1 bg-[radial-gradient(ellipse_at_center,var(--color-slate-900),var(--color-slate-950))] lg:h-auto">
      <VideoPreview
        bind:this={preview}
        {scenes}
        projectTitle={project.title}
        aspectRatio={project.aspect_ratio}
        onaspect={onaspect}
        language={project.language}
        purpose={project.purpose}
        presenter={project.presenter}
        avatar={project.avatar_resolved}
        ctaText={project.cta_text}
        music={project.music}
        musicUrl={project.music_url}
        fps={project.fps}
        width={project.width}
        height={project.height}
        {hidden}
        {muted}
        bind:time
        bind:playing
        bind:selectedId
        bind:selectedLayerId
        onlayercommit={patchLayer}
        onlayeredit={(layerId) => {
          selectedLayerId = layerId;
          textfocus += 1;
        }}
      />
    </main>

    <PropertiesPanel
      scene={selected}
      bind:selectedLayerId
      {textfocus}
      busy={saving}
      onsave={onsaveScene}
      ondelete={ondeleteScene}
      onduplicate={onduplicateScene}
      {onregenerateVoice}
      {onsettings}
      {onlayers}
      onopencaptions={() => (tool = 'captions')}
      onupload={uploadToScene}
      {onclearmedia}
    />
  </div>

  <!-- timeline: toolbar + tracks, height adjustable -->
  <div class="flex shrink-0 flex-col" style="height:{timelineHeight}px">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="group relative z-10 h-1.5 shrink-0 cursor-row-resize bg-slate-800 transition hover:bg-sun-500/60"
      title={t('editor.top.resizeTimeline')}
      onpointerdown={startResize}
    >
      <span class="absolute top-1/2 left-1/2 h-0.5 w-10 -translate-x-1/2 -translate-y-1/2 rounded bg-slate-600 group-hover:bg-sun-200"></span>
    </div>
    <EditorToolbar
      canSplit={!!underPlayhead}
      hasSelection={!!selected}
      {pps}
      onsplit={split}
      ondelete={deleteSelected}
      onduplicate={duplicateSelected}
      onzoom={(value) => (zoom = clamp(value, 2, 600))}
      onzoomin={() => zoomBy(1.4)}
      onzoomout={() => zoomBy(1 / 1.4)}
      onfit={() => (zoom = null)}
    />
    <div class="min-h-0 flex-1">
      <Timeline
        {scenes}
        {project}
        bind:time
        bind:selectedId
        bind:selectedLayerId
        bind:zoom
        bind:pps
        {locked}
        {hidden}
        {muted}
        ontoggle={toggleTrack}
        {onreorder}
        {onresize}
        {ontrim}
        onlayer={patchLayer}
        oncaption={(sceneId, start) => {
          selectedId = sceneId;
          selectedLayerId = null;
          time = clamp(startOf(sceneId) + start + 0.01, 0, total);
          tool = 'captions';
        }}
      />
    </div>
  </div>
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

{#if choosingHost}
  <Modal wide title={t('avatars.create.chooseTitle')} onclose={() => (choosingHost = false)}>
    <div class="max-h-[68vh] overflow-y-auto pr-1">
    <AvatarPicker
      allowAuto
      value={project.avatar}
      onselect={(id) => {
        choosingHost = false;
        if (id !== project.avatar) onavatar(id);
      }}
    />
    </div>
  </Modal>
{/if}
