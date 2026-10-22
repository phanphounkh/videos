<script lang="ts">
  /**
   * The editor shell: top bar, scene list / media library, preview, properties
   * panel, toolbar and timeline, plus the keyboard shortcuts.
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
  import EditorToolbar from '$lib/components/editor/EditorToolbar.svelte';
  import ExportDialog from '$lib/components/editor/ExportDialog.svelte';
  import MediaLibrary from '$lib/components/editor/MediaLibrary.svelte';
  import PropertiesPanel, { type Tab } from '$lib/components/editor/PropertiesPanel.svelte';
  import SceneList from '$lib/components/editor/SceneList.svelte';
  import Timeline from '$lib/components/editor/Timeline.svelte';
  import VideoPreview from '$lib/components/editor/VideoPreview.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
  import { clamp, layersOf, makeLayer, newId, round } from '$lib/editor/layers';
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
    saveLabel = 'Saved',
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
    onstartRender: () => void;
  } = $props();

  // ---------------------------------------------------------------- UI state
  let selectedId = $state<string | null>(null);
  let selectedLayerId = $state<string | null>(null);
  let time = $state(0);
  let playing = $state(false);
  let tab = $state<Tab>('scene');
  let leftTab = $state<'scenes' | 'media'>('scenes');
  let zoom = $state<number | null>(null);
  let pps = $state(40);
  let textfocus = $state(0);
  let exportOpen = $state(false);
  let preview = $state<{ toggle: () => void }>();
  let mediaInput = $state<HTMLInputElement>();
  let hint = $state<string | null>(null);

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
  // Choosing a text/sticker brings up its controls.
  let lastLayer: string | null = null;
  $effect(() => {
    if (selectedLayerId && selectedLayerId !== lastLayer) tab = 'layer';
    lastLayer = selectedLayerId;
  });

  // ---------------------------------------------------------------- actions
  function seekToScene(id: string) {
    selectedId = id;
    selectedLayerId = null;
    time = startOf(id) + 0.05;
  }

  function split() {
    const here = underPlayhead;
    if (!here) return tell('There is nothing to split yet.');
    const { scene, at } = here;
    if (at < 0.2 || scene.duration - at < 0.2) {
      return tell('Move the playhead inside a scene (at least 0.2s from its edges) to split it.');
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
  function addLayer(kind: 'text' | 'sticker') {
    const here = underPlayhead;
    if (!here) return tell('Add a scene first.');
    const layer = makeLayer(kind, here.scene, here.at, project.language);
    selectedId = here.scene.id;
    selectedLayerId = layer.id;
    tab = 'layer';
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
    if (!sceneId) return tell('Select a scene first, or add the file from the Media tab.');
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
</script>

<svelte:window {onkeydown} />

<div class="flex h-full min-h-0 flex-col overflow-y-auto bg-slate-950 lg:overflow-hidden">
  <!-- project bar -->
  <header class="flex h-14 shrink-0 items-center gap-3 border-b border-slate-800 bg-slate-900 px-3">
    <a
      href="/projects"
      class="grid h-8 w-8 place-items-center rounded-lg text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
      title="Back to projects"
      aria-label="Back to projects"
    >
      <Icon name="arrowLeft" size={17} />
    </a>

    <input
      bind:value={titleDraft}
      onblur={() => titleDraft !== project.title && onrename(titleDraft)}
      onkeydown={(e) => e.key === 'Enter' && e.currentTarget.blur()}
      class="!h-9 min-w-0 max-w-xl flex-1 !border-transparent !bg-transparent px-2 text-[15px] font-semibold text-slate-50 hover:!border-slate-700 focus:!bg-slate-950"
      aria-label="Project title"
    />

    <span class="hidden items-center gap-3 text-xs text-slate-500 md:flex">
      {#if notice}
        <span
          class="inline-flex items-center gap-1.5 rounded-full bg-sun-400/10 px-2.5 py-1 text-xs font-medium text-sun-200"
          title={notice}
          role="status"
        >
          <span class="h-1.5 w-1.5 animate-pulse rounded-full bg-sun-400"></span>
          Generating narration…
        </span>
      {:else}
        <StatusBadge status={project.status} />
      {/if}
      <span class="inline-flex items-center gap-1.5">
        {#if saving}
          <span class="h-3 w-3 animate-spin rounded-full border-2 border-slate-500 border-t-transparent"></span>
          Saving…
        {:else}
          <Icon name="check" size={13} class="text-emerald-400" />
          {saveLabel}
        {/if}
      </span>
      <span class="hidden xl:inline">{project.width}×{project.height} · {project.fps}fps</span>
    </span>

    <span class="flex-1"></span>

    <div class="flex items-center gap-0.5 rounded-lg border border-slate-800 bg-slate-950 p-0.5">
      <button
        class="grid h-8 w-8 place-items-center rounded-md text-slate-300 transition hover:bg-slate-800 disabled:opacity-35 disabled:hover:bg-transparent"
        disabled={!canUndo}
        onclick={onundo}
        title="Undo (Ctrl+Z)"
        aria-label="Undo"><Icon name="undo" size={16} /></button
      >
      <button
        class="grid h-8 w-8 place-items-center rounded-md text-slate-300 transition hover:bg-slate-800 disabled:opacity-35 disabled:hover:bg-transparent"
        disabled={!canRedo}
        onclick={onredo}
        title="Redo (Ctrl+Shift+Z)"
        aria-label="Redo"><Icon name="redo" size={16} /></button
      >
    </div>

    <label
      class="hidden cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-800 sm:flex"
      title="Show the animated host"
    >
      <input
        type="checkbox"
        checked={project.presenter}
        onchange={(e) => onpresenter(e.currentTarget.checked)}
      />
      Host
    </label>

    {#if !project.language.startsWith('km')}
      <Button variant="secondary" size="sm" onclick={onmakeKhmer} loading={saving}>
        Khmer version
      </Button>
    {/if}
    <Button icon="download" onclick={() => (exportOpen = true)}>Export</Button>
  </header>

  {#if error}
    <div class="shrink-0 border-b border-slate-800 bg-slate-900/60 px-3 py-2">
      <ErrorBanner {error} />
    </div>
  {/if}

  <!-- workspace: media | stage | inspector -->
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

    <aside
      class="flex max-h-80 w-full shrink-0 flex-col border-b border-slate-800 bg-slate-900/40 lg:max-h-none lg:w-[19rem] lg:border-r lg:border-b-0"
    >
      <div class="flex shrink-0 gap-1 border-b border-slate-800 p-2" role="tablist">
        {#each [{ id: 'scenes', label: 'Scenes', icon: 'film' }, { id: 'media', label: 'Media', icon: 'image' }] as const as item (item.id)}
          <button
            role="tab"
            aria-selected={leftTab === item.id}
            class="flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold transition {leftTab ===
            item.id
              ? 'bg-slate-800 text-slate-50'
              : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'}"
            onclick={() => (leftTab = item.id)}
          >
            <Icon name={item.icon} size={14} />
            {item.label}
          </button>
        {/each}
      </div>
      <div class="min-h-0 flex-1 overflow-y-auto p-3">
        {#if leftTab === 'scenes'}
          <SceneList {scenes} {selectedId} onselect={seekToScene} {onreorder} onadd={onaddScene} />
        {:else}
          <MediaLibrary
            {media}
            hasScene={!!selected}
            onupload={(file) => onuploadMedia(file, null)}
            onuse={(asset) => selected && onusemedia(selected.id, asset)}
            onaddscene={addMediaScene}
          />
        {/if}
      </div>
    </aside>

    <main class="h-[26rem] min-w-0 flex-1 bg-[radial-gradient(ellipse_at_center,var(--color-slate-900),var(--color-slate-950))] lg:h-auto">
      <VideoPreview
        bind:this={preview}
        {scenes}
        projectTitle={project.title}
        aspectRatio={project.aspect_ratio}
        language={project.language}
        purpose={project.purpose}
        presenter={project.presenter}
        ctaText={project.cta_text}
        music={project.music}
        musicUrl={project.music_url}
        fps={project.fps}
        width={project.width}
        height={project.height}
        bind:time
        bind:playing
        bind:selectedId
        bind:selectedLayerId
        onlayercommit={patchLayer}
        onlayeredit={(layerId) => {
          selectedLayerId = layerId;
          tab = 'layer';
          textfocus += 1;
        }}
      />
    </main>

    <PropertiesPanel
      scene={selected}
      {project}
      bind:tab
      bind:selectedLayerId
      {textfocus}
      busy={saving}
      onsave={onsaveScene}
      ondelete={ondeleteScene}
      onduplicate={onduplicateScene}
      {onregenerateVoice}
      {onsettings}
      {onlayers}
      {oncaptions}
      {onresetcaptions}
      onseek={(seconds) => selected && (time = clamp(startOf(selected.id) + seconds, 0, total))}
      playhead={selected && underPlayhead?.scene.id === selected.id ? underPlayhead.at : -1}
      onaddlayer={addLayer}
      onupload={uploadToScene}
      {onclearmedia}
      {onuploadMusic}
      {onremoveMusic}
      {onmusic}
    />
  </div>

  <!-- timeline: toolbar + tracks, height adjustable -->
  <div class="flex shrink-0 flex-col" style="height:{timelineHeight}px">
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div
      class="group relative z-10 h-1.5 shrink-0 cursor-row-resize bg-slate-800 transition hover:bg-sun-500/60"
      title="Drag to resize the timeline"
      onpointerdown={startResize}
    >
      <span class="absolute top-1/2 left-1/2 h-0.5 w-10 -translate-x-1/2 -translate-y-1/2 rounded bg-slate-600 group-hover:bg-sun-200"></span>
    </div>
    <EditorToolbar
      canSplit={!!underPlayhead}
      hasSelection={!!selected}
      onsplit={split}
      ondelete={deleteSelected}
      onduplicate={duplicateSelected}
      onaddtext={() => addLayer('text')}
      onaddsticker={() => addLayer('sticker')}
      onupload={() => (selected ? mediaInput?.click() : tell('Select a scene first.'))}
      onzoomin={() => zoomBy(1.4)}
      onzoomout={() => zoomBy(1 / 1.4)}
      onfit={() => (zoom = null)}
    />
    <input
      bind:this={mediaInput}
      type="file"
      accept="image/png,image/jpeg,image/webp,video/mp4,video/webm,.png,.jpg,.jpeg,.webp,.mp4,.webm"
      class="hidden"
      onchange={(e) => {
        const file = e.currentTarget.files?.[0];
        e.currentTarget.value = '';
        if (file) uploadToScene(file, selectedId);
      }}
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
        {onreorder}
        {onresize}
        {ontrim}
        onlayer={patchLayer}
        oncaption={(sceneId, start) => {
          selectedId = sceneId;
          selectedLayerId = null;
          time = clamp(startOf(sceneId) + start + 0.01, 0, total);
          tab = 'captions';
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
