<script lang="ts">
  /**
   * Editor preview. Runs the renderer's real Remotion composition (see
   * $lib/remotion/player.tsx), so what plays here is exactly what exports:
   * presenter, lip-sync, karaoke captions, music and sound effects.
   */
  import { onMount } from 'svelte';
  import CanvasOverlay from '$lib/components/editor/CanvasOverlay.svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import { measure, reportError } from '$lib/telemetry/client';
  import { layersOf } from '$lib/editor/layers';
  import { customHosts, loadHosts } from '$lib/components/avatars/hosts.svelte';
  import { buildPayload } from '$lib/remotion/payload';
  import type { PreviewController } from '$lib/remotion/player';
  import { t } from '$lib/i18n/index.svelte';
  import type { Layer, Project, Scene } from '$lib/types/api';

  /** 0 fits the whole video in the stage; otherwise a multiple of that fitted size. */
  let zoomLevel = $state(0);

  const SIZES: Record<string, [number, number]> = {
    '9:16': [1080, 1920],
    '1:1': [1080, 1080],
    '16:9': [1920, 1080]
  };

  let {
    scenes,
    projectTitle = 'Sorya',
    aspectRatio = '16:9',
    language = 'km',
    purpose = 'story',
    presenter = true,
    ctaText = null,
    avatar = null,
    music = undefined,
    musicUrl = null,
    fps = 30,
    width = undefined,
    height = undefined,
    time = $bindable(0),
    playing = $bindable(false),
    selectedId = $bindable<string | null>(null),
    selectedLayerId = $bindable<string | null>(null),
    muted = { title: false, video: false, voice: false, captions: false, music: false },
    hidden = { title: false, video: false, voice: false, captions: false, music: false },
    onaspect,
    onlayercommit,
    onlayeredit
  }: {
    scenes: Scene[];
    /** Called with a new ratio; when absent the chip is read-only. */
    onaspect?: (ratio: string) => void;
    projectTitle?: string;
    aspectRatio?: string;
    language?: string;
    purpose?: Project['purpose'];
    presenter?: boolean;
    ctaText?: string | null;
    /** The host's id: a built-in one (`real-f-adult`) or an uploaded one (`custom:<uuid>`). */
    avatar?: string | null;
    music?: Project['music'];
    musicUrl?: string | null;
    fps?: number;
    width?: number;
    height?: number;
    time?: number;
    playing?: boolean;
    selectedId?: string | null;
    selectedLayerId?: string | null;
    /** Editor-local track toggles (never saved or exported): muted audio, hidden content. */
    muted?: Record<string, boolean>;
    hidden?: Record<string, boolean>;
    onlayercommit: (sceneId: string, layerId: string, patch: Partial<Layer>) => void;
    onlayeredit: (layerId: string) => void;
  } = $props();

  let host: HTMLDivElement;
  let controller: PreviewController | null = null;

  /** Play or pause (the editor's Space key). */
  export function toggle() {
    controller?.toggle();
  }
  // Last frame reported by the player, so seeks we caused are not echoed back.
  let reportedFrame = -1;

  const size = $derived(width && height ? [width, height] : (SIZES[aspectRatio] ?? SIZES['16:9']));
  const total = $derived(scenes.reduce((sum, scene) => sum + scene.duration, 0));
  const clock = (seconds: number): string => {
    const whole = Math.max(0, Math.floor(seconds));
    return `${String(Math.floor(whole / 60)).padStart(2, '0')}:${String(whole % 60).padStart(2, '0')}`;
  };
  const sorted = $derived([...scenes].sort((a, b) => a.scene_number - b.scene_number));
  const nudge = (seconds: number) => (time = Math.min(Math.max(time + seconds, 0), total));
  /** Jump to the start of the previous scene (or this one, when well into it) or the next. */
  function jump(direction: -1 | 1) {
    const starts: number[] = [];
    let cursor = 0;
    for (const scene of sorted) {
      starts.push(cursor);
      cursor += scene.duration;
    }
    if (direction === 1) {
      const next = starts.find((start) => start > time + 0.05);
      time = next ?? Math.max(0, total - 0.05);
    } else {
      const before = starts.filter((start) => start < time - 0.5);
      time = before.at(-1) ?? 0;
    }
  }
  function fullscreen() {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void stage?.requestFullscreen?.();
  }
  // A layer being dragged on the canvas: shown live in the player before it is saved.
  let draft = $state<{ layerId: string; patch: Partial<Layer> } | null>(null);

  // Preview-only controls: volume, safe guides and the editor's track toggles.
  let volume = $state(1);
  let guides = $state(false);
  let stage = $state<HTMLDivElement>();

  const withDraft = $derived(
    draft
      ? scenes.map((scene) => {
          const layers = layersOf(scene);
          if (!layers.some((layer) => layer.id === draft!.layerId)) return scene;
          return {
            ...scene,
            settings: {
              ...scene.settings,
              layers: layers.map((layer) =>
                layer.id === draft!.layerId ? { ...layer, ...draft!.patch } : layer
              )
            }
          };
        })
      : scenes
  );

  // The track toggles and the volume slider reshape what the player is given; the
  // saved scenes are untouched, so none of this reaches an export.
  const gain = (value: unknown, fallback: number, off: boolean): number =>
    off ? 0 : (typeof value === 'number' ? value : fallback) * volume;
  const shown = $derived(
    volume === 1 && !Object.values(hidden).some(Boolean) && !Object.values(muted).some(Boolean)
      ? withDraft
      : withDraft.map((scene) => ({
          ...scene,
          image_url: hidden.video ? null : scene.image_url,
          video_url: hidden.video ? null : scene.video_url,
          captions: hidden.captions ? [] : scene.captions,
          settings: {
            ...scene.settings,
            layers: hidden.title ? [] : scene.settings?.layers,
            voice_volume: gain(scene.settings?.voice_volume, 1, muted.voice),
            clip_volume: gain(scene.settings?.clip_volume, 0, muted.video)
          }
        }))
  );
  const previewMusic = $derived(
    music && (muted.music || volume !== 1)
      ? { ...music, enabled: muted.music ? false : music.enabled, volume: music.volume * volume }
      : music
  );

  // The host to draw: a built-in avatar, or the person's own photo with its chosen mode.
  $effect(() => {
    void loadHosts().catch(() => {});
  });
  const avatarPayload = $derived.by(() => {
    if (!avatar) return undefined;
    const custom = customHosts().find((c) => c.id === avatar);
    return custom
      ? ({ kind: 'photo', id: avatar, imageUrl: custom.image_url, mode: custom.mode } as const)
      : ({ kind: 'builtin', id: avatar, imageUrl: null, mode: 'mouth' } as const);
  });

  const built = $derived.by(() => {
    if (!shown.length) return { payload: null, error: null };
    try {
      return {
        payload: buildPayload(
          {
            title: projectTitle,
            language,
            fps,
            width: size[0],
            height: size[1],
            purpose,
            presenter,
            avatar: avatarPayload,
            cta_text: ctaText,
            music: previewMusic,
            music_url: musicUrl
          },
          shown
        ),
        error: null
      };
    } catch (e) {
      return { payload: null, error: e instanceof Error ? e.message : String(e) };
    }
  });

  // The scene under the playhead, and which of its layers are on screen now.
  const current = $derived.by(() => {
    let cursor = 0;
    for (const scene of [...scenes].sort((a, b) => a.scene_number - b.scene_number)) {
      if (time < cursor + scene.duration) return { scene, at: time - cursor };
      cursor += scene.duration;
    }
    return null;
  });
  const activeLayers = $derived(
    current && !hidden.title
      ? layersOf(current.scene).filter((l) => current.at >= l.start && current.at < l.end)
      : []
  );

  /** The scene under the playhead, by cumulative duration. */
  function sceneAt(seconds: number): Scene | null {
    let cursor = 0;
    for (const scene of [...scenes].sort((a, b) => a.scene_number - b.scene_number)) {
      cursor += scene.duration;
      if (seconds < cursor) return scene;
    }
    return scenes.at(-1) ?? null;
  }

  // Frames counted while playing, for the frame-rate measurement.
  let played = { since: 0, frames: 0 };

  // A scene the preview cannot build is a bug worth knowing about.
  $effect(() => {
    if (built.error) reportError('preview.error', built.error);
  });

  let mountPreview = $state<typeof import('$lib/remotion/player').mountPreview | null>(null);

  onMount(() => {
    // React and Remotion load only in the browser, and only for the editor.
    void import('$lib/remotion/player').then((module) => (mountPreview = module.mountPreview));
    return () => {
      controller?.destroy();
      controller = null;
    };
  });

  // Mount once there is something to play, then feed it every edit.
  $effect(() => {
    const payload = built.payload;
    if (!payload || !mountPreview) return;
    if (controller) {
      controller.update(payload);
      return;
    }
    const mountStarted = performance.now();
    let mountReported = false;
    controller = mountPreview(host, payload, {
      onFrame: (frame) => {
        if (!mountReported) {
          mountReported = true;
          measure('preview.mount', { duration_ms: performance.now() - mountStarted });
        }
        if (playing) played.frames += 1;
        reportedFrame = frame;
        time = frame / fps;
        const current = sceneAt(time);
        if (playing && current && current.id !== selectedId) selectedId = current.id;
      },
      onPlaying: (value) => {
        playing = value;
        if (value) {
          played = { since: performance.now(), frames: 0 };
        } else if (played.since) {
          // Frames per second the player really managed while playing. A short
          // burst says nothing, so only runs of two seconds or more are reported.
          const seconds = (performance.now() - played.since) / 1000;
          if (seconds >= 2) {
            measure('preview.fps', {
              value: Math.round((played.frames / seconds) * 10) / 10,
              props: { target: fps }
            });
          }
          played = { since: 0, frames: 0 };
        }
      }
    });
    reportedFrame = Math.round(time * fps);
    controller.seek(reportedFrame);
  });

  // Follow playhead changes made elsewhere (slider, timeline, scene list).
  $effect(() => {
    const frame = Math.round(time * fps);
    if (controller && frame !== reportedFrame) {
      reportedFrame = frame;
      controller.seek(frame);
    }
  });
</script>

<!-- The stage: the video is fitted into whatever room the editor leaves, never cropped. -->
<div class="flex h-full min-h-0 flex-col">
  <div bind:this={stage} class="min-h-0 flex-1 bg-slate-950 px-4 pb-2 [container-type:size]">
    <div class="flex h-full w-full overflow-auto">
      <div
        class="relative m-auto shrink-0 overflow-hidden rounded-lg bg-black shadow-pop ring-1 ring-white/10"
        style="aspect-ratio:{size[0]} / {size[1]}; width:calc(min(100cqw, 100cqh * {size[0]} / {size[1]}) * {zoomLevel || 1})"
      >
        <div bind:this={host} class="absolute inset-0"></div>
        {#if scenes.length && !built.error}
          <CanvasOverlay
            layers={activeLayers}
            bind:selectedLayerId
            compWidth={size[0]}
            compHeight={size[1]}
            {language}
            ondraft={(layerId, patch) => (draft = patch ? { layerId, patch } : null)}
            oncommit={(layerId, patch) => current && onlayercommit(current.scene.id, layerId, patch)}
            onedit={onlayeredit}
          />
        {/if}
        {#if guides}
          <!-- action-safe area (90%): an editing aid, never part of the export -->
          <div
            class="pointer-events-none absolute inset-[5%] rounded-sm border border-dashed border-white/60"
            aria-hidden="true"
          ></div>
        {/if}
        {#if !scenes.length}
          <div class="absolute inset-0 flex items-center justify-center text-sm text-slate-400">
            {t('editor.preview.noScenes')}
          </div>
        {:else if built.error}
          <div
            class="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-red-300"
          >
            {t('editor.preview.unavailable', { error: built.error })}
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- scrub bar -->
  <div class="shrink-0 px-5 pt-1">
    <input
      type="range"
      min="0"
      max={Math.max(total, 0.1)}
      step="0.05"
      bind:value={time}
      class="block h-1.5 w-full cursor-pointer accent-sun-500"
      aria-label={t('editor.preview.playhead')}
    />
  </div>

  <!-- transport -->
  <div class="grid shrink-0 grid-cols-[1fr_auto_1fr] items-center gap-3 px-4 py-2">
    <span class="font-mono text-xs whitespace-nowrap text-slate-300 tabular-nums">
      {clock(time)} <span class="text-slate-500">/ {clock(total)}</span>
    </span>

    <div class="flex items-center gap-1">
      {#snippet step(icon: IconName, label: string, click: () => void, flip = false)}
        <button
          class="grid h-8 w-8 place-items-center rounded-lg text-slate-300 transition hover:bg-slate-800 hover:text-slate-50 disabled:opacity-35"
          onclick={click}
          disabled={!scenes.length}
          title={label}
          aria-label={label}
        >
          <span class={flip ? 'grid -scale-x-100' : 'grid'}><Icon name={icon} size={16} /></span>
        </button>
      {/snippet}
      {@render step('skipBack', t('editor.preview.prevScene'), () => jump(-1))}
      {@render step('rewind', t('editor.preview.back5'), () => nudge(-5))}
      <button
        class="mx-1 grid h-10 w-10 shrink-0 place-items-center rounded-full bg-[image:var(--sun-gradient)] text-sun-950 shadow-[0_6px_18px_-6px_rgb(255_138_31/0.7)] transition hover:brightness-110 disabled:opacity-40"
        onclick={() => controller?.toggle()}
        disabled={!scenes.length}
        title={t('editor.preview.playPause')}
        aria-label={playing ? t('editor.preview.pause') : t('editor.preview.play')}
      >
        <Icon name={playing ? 'pause' : 'play'} size={18} />
      </button>
      {@render step('rewind', t('editor.preview.fwd5'), () => nudge(5), true)}
      {@render step('skipBack', t('editor.preview.nextScene'), () => jump(1), true)}
    </div>

    <div class="flex items-center justify-end gap-2">
      <label
        class="inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs font-medium text-slate-300 transition hover:bg-slate-800 hover:text-slate-50 focus-within:bg-slate-800"
        title={t('editor.preview.aspect', { size: `${size[0]}×${size[1]}` })}
      >
        <Icon name="video" size={15} />
        <select
          class="h-6 cursor-pointer rounded-none border-0 bg-transparent pr-5 pl-0 text-xs font-medium text-slate-300 shadow-none [field-sizing:content] [background-position:right_center] hover:border-0 focus:border-0 focus:shadow-none"
          aria-label={t('editor.preview.aspectLabel')}
          value={aspectRatio}
          disabled={!onaspect}
          onchange={(e) => onaspect?.(e.currentTarget.value)}
        >
          {#each Object.keys(SIZES) as r (r)}<option value={r}>{r}</option>{/each}
        </select>
      </label>
      <label class="inline-flex h-8 items-center gap-1 rounded-lg px-2 text-xs font-medium text-slate-300 transition hover:bg-slate-800 hover:text-slate-50 focus-within:bg-slate-800" title={t('editor.preview.fitTip')}>
        <Icon name="fit" size={15} />
        <select class="h-6 cursor-pointer rounded-none border-0 bg-transparent pr-5 pl-0 text-xs font-medium text-slate-300 shadow-none [field-sizing:content] [background-position:right_center] hover:border-0 focus:border-0 focus:shadow-none" aria-label={t('editor.tl.fit')} bind:value={zoomLevel}>
          <option value={0}>{t('editor.tl.fit')}</option>
          {#each [0.5, 0.75, 1, 1.5, 2] as z (z)}<option value={z}>{Math.round(z * 100)}%</option>{/each}
        </select>
      </label>
      <span class="hidden items-center gap-1.5 text-slate-400 md:inline-flex" title={t('editor.preview.volumeTip')}>
        <Icon name="volume" size={15} />
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          bind:value={volume}
          class="h-1 w-20 cursor-pointer accent-sun-500"
          aria-label={t('editor.preview.volume')}
        />
      </span>
      <button
        class="inline-flex h-8 items-center gap-1.5 rounded-lg px-2 text-xs font-medium transition {guides
          ? 'bg-sun-400/15 text-sun-200'
          : 'text-slate-300 hover:bg-slate-800 hover:text-slate-50'}"
        aria-pressed={guides}
        title={t('editor.preview.guidesTip')}
        onclick={() => (guides = !guides)}
      >
        <Icon name="grid" size={15} />
        <span class="hidden whitespace-nowrap 2xl:inline">{t('editor.preview.guides')}</span>
      </button>
      <button
        class="grid h-8 w-8 place-items-center rounded-lg text-slate-300 transition hover:bg-slate-800 hover:text-slate-50"
        title={t('editor.preview.fullscreen')}
        aria-label={t('editor.preview.fullscreen')}
        onclick={fullscreen}
      >
        <Icon name="maximize" size={16} />
      </button>
    </div>
  </div>
</div>
