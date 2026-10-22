<script lang="ts">
  /**
   * Editor preview. Runs the renderer's real Remotion composition (see
   * $lib/remotion/player.tsx), so what plays here is exactly what exports:
   * presenter, lip-sync, karaoke captions, music and sound effects.
   */
  import { onMount } from 'svelte';
  import CanvasOverlay from '$lib/components/editor/CanvasOverlay.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import { layersOf } from '$lib/editor/layers';
  import { buildPayload } from '$lib/remotion/payload';
  import type { PreviewController } from '$lib/remotion/player';
  import type { Layer, Project, Scene } from '$lib/types/api';

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
    music = undefined,
    musicUrl = null,
    fps = 30,
    width = undefined,
    height = undefined,
    time = $bindable(0),
    playing = $bindable(false),
    selectedId = $bindable<string | null>(null),
    selectedLayerId = $bindable<string | null>(null),
    onlayercommit,
    onlayeredit
  }: {
    scenes: Scene[];
    projectTitle?: string;
    aspectRatio?: string;
    language?: string;
    purpose?: Project['purpose'];
    presenter?: boolean;
    ctaText?: string | null;
    music?: Project['music'];
    musicUrl?: string | null;
    fps?: number;
    width?: number;
    height?: number;
    time?: number;
    playing?: boolean;
    selectedId?: string | null;
    selectedLayerId?: string | null;
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
    const whole = Math.max(0, seconds);
    const m = Math.floor(whole / 60);
    return `${m}:${(whole - m * 60).toFixed(1).padStart(4, '0')}`;
  };
  // A layer being dragged on the canvas: shown live in the player before it is saved.
  let draft = $state<{ layerId: string; patch: Partial<Layer> } | null>(null);

  const shown = $derived(
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
            cta_text: ctaText,
            music,
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
    current
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
    controller = mountPreview(host, payload, {
      onFrame: (frame) => {
        reportedFrame = frame;
        time = frame / fps;
        const current = sceneAt(time);
        if (playing && current && current.id !== selectedId) selectedId = current.id;
      },
      onPlaying: (value) => (playing = value)
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
  <div class="min-h-0 flex-1 p-4 [container-type:size]">
    <div class="flex h-full w-full items-center justify-center">
      <div
        class="relative overflow-hidden rounded-lg bg-black shadow-pop ring-1 ring-white/10"
        style="aspect-ratio:{size[0]} / {size[1]}; width:min(100cqw, calc(100cqh * {size[0]} / {size[1]}))"
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
        {#if !scenes.length}
          <div class="absolute inset-0 flex items-center justify-center text-sm text-slate-400">
            No scenes yet
          </div>
        {:else if built.error}
          <div
            class="absolute inset-0 flex items-center justify-center p-6 text-center text-sm text-red-300"
          >
            Preview unavailable: {built.error}
          </div>
        {/if}
      </div>
    </div>
  </div>

  <!-- transport -->
  <div class="flex items-center gap-3 border-t border-slate-800 px-4 py-2">
    <button
      class="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-[image:var(--sun-gradient)] text-sun-950 shadow-[0_6px_18px_-6px_rgb(255_138_31/0.7)] transition hover:brightness-110 disabled:opacity-40"
      onclick={() => controller?.toggle()}
      disabled={!scenes.length}
      title="Play / pause (Space)"
      aria-label={playing ? 'Pause' : 'Play'}
    >
      <Icon name={playing ? 'pause' : 'play'} size={16} />
    </button>
    <span class="shrink-0 font-mono text-xs whitespace-nowrap text-slate-300 tabular-nums">
      {clock(time)} <span class="text-slate-500">/ {clock(total)}</span>
    </span>
    <input
      type="range"
      min="0"
      max={Math.max(total, 0.1)}
      step="0.05"
      bind:value={time}
      class="h-1.5 min-w-0 flex-1 cursor-pointer"
      aria-label="Playhead"
    />
  </div>
</div>
