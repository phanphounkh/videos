<script lang="ts">
  /**
   * The editing timeline.
   *
   * Tracks (top to bottom): text and stickers, video, voice, captions, music.
   *
   *   scrub        press the ruler (or any empty track) and drag
   *   reorder      drag a scene clip sideways and drop it between two others
   *   trim         drag a scene clip's left or right edge
   *   overlays     drag a text/sticker clip to move it in time, drag its edges to
   *                change when it appears and disappears (inside its own scene)
   *   zoom         the toolbar's zoom controls, or ctrl + wheel
   *   track toggles  lock / eye / volume per track are editor-local: lock stops edits
   *                on that track, eye and volume only change the preview (VideoEditor)
   *
   * Nothing here talks to the server. Drags are drawn from local state and,
   * when the pointer is released, ONE callback reports the result.
   */
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import { clamp, layersOf, round } from '$lib/editor/layers';
  import { t } from '$lib/i18n/index.svelte';
  import type { Layer, Project, Scene } from '$lib/types/api';

  let {
    scenes,
    project,
    time = $bindable(0),
    selectedId = $bindable<string | null>(null),
    selectedLayerId = $bindable<string | null>(null),
    zoom = $bindable<number | null>(null),
    pps = $bindable(40),
    locked = {},
    hidden = {},
    muted = {},
    ontoggle,
    onreorder,
    onresize,
    ontrim,
    onlayer,
    oncaption
  }: {
    scenes: Scene[];
    project: Pick<Project, 'music' | 'music_url' | 'music_name' | 'music_duration'>;
    time?: number;
    selectedId?: string | null;
    selectedLayerId?: string | null;
    /** Pixels per second; null fits the whole video in the view. */
    zoom?: number | null;
    /** The pixels per second in use, for the toolbar's zoom buttons. */
    pps?: number;
    /** Per-track editor-local flags, keyed title | video | voice | captions | music. */
    locked?: Record<string, boolean>;
    hidden?: Record<string, boolean>;
    muted?: Record<string, boolean>;
    ontoggle: (track: string, flag: 'locked' | 'hidden' | 'muted') => void;
    onreorder: (ids: string[]) => void;
    onresize: (id: string, duration: number) => void;
    ontrim: (id: string, start: number, end: number) => void;
    onlayer: (sceneId: string, layerId: string, patch: { start: number; end: number }) => void;
    /** A caption bar was clicked: select its scene and move the playhead there. */
    oncaption: (sceneId: string, start: number) => void;
  } = $props();

  const MIN_CLIP = 0.5; // shortest scene
  const MIN_LAYER = 0.2; // shortest overlay
  const SNAP_PX = 8;
  /** A stable pseudo-waveform for a scene's voice bar: the same scene always looks the same,
   * and the bars thin out as you zoom out. It is a visual cue, not the audio's real shape. */
  function bars(id: string, width: number): number[] {
    const count = Math.max(4, Math.min(240, Math.round(width / 3)));
    let seed = 0;
    for (const ch of id) seed = (seed * 31 + ch.charCodeAt(0)) >>> 0;
    return Array.from({ length: count }, () => {
      seed = (seed * 1664525 + 1013904223) >>> 0;
      return 2 + (seed / 2 ** 32) * 7;
    });
  }

  const ROW = { ruler: 30, lane: 34, video: 64, voice: 36, captions: 34, music: 36 };
  const LABEL = 116; // width of the sticky track-header column

  // ------------------------------------------------------------------ geometry
  let viewport = $state(800);
  let scroller = $state<HTMLDivElement>();
  let content = $state<HTMLDivElement>();

  type Drag =
    | { kind: 'scrub' }
    | { kind: 'move'; id: string; startX: number; dx: number; moved: boolean }
    | { kind: 'right' | 'left'; id: string; startX: number; value: number }
    | {
        kind: 'lmove' | 'lleft' | 'lright';
        sceneId: string;
        layerId: string;
        startX: number;
        start: number;
        end: number;
        orig: { start: number; end: number };
      };
  let drag = $state<Drag | null>(null);

  const ordered = $derived([...scenes].sort((a, b) => a.scene_number - b.scene_number));

  /** A scene's length on screen: what the pointer is making it, else what it is. */
  const lengthOf = (scene: Scene): number => {
    if (drag && (drag.kind === 'right' || drag.kind === 'left') && drag.id === scene.id) {
      return drag.value;
    }
    return scene.duration;
  };

  const starts = $derived.by(() => {
    const out = new Map<string, number>();
    let cursor = 0;
    for (const scene of ordered) {
      out.set(scene.id, cursor);
      cursor += lengthOf(scene);
    }
    return out;
  });
  const total = $derived(Math.max(ordered.reduce((sum, s) => sum + lengthOf(s), 0), 0.001));

  const fit = $derived(clamp((viewport - LABEL - 32) / total, 2, 600));
  const scale = $derived(zoom ?? fit);
  $effect(() => {
    pps = scale;
  });
  const width = $derived(Math.max(total * scale + 64, viewport - LABEL));
  const px = (seconds: number) => seconds * scale;

  // ---------------------------------------------------------------- ruler ticks
  const tickStep = $derived(
    [0.1, 0.25, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300].find((step) => step * scale >= 72) ?? 300
  );
  const ticks = $derived(
    Array.from({ length: Math.floor(total / tickStep) + 2 }, (_, i) => round(i * tickStep, 3))
  );
  const stamp = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = seconds - m * 60;
    const text = tickStep < 1 ? s.toFixed(1).padStart(4, '0') : String(Math.round(s)).padStart(2, '0');
    return `${m}:${text}`;
  };

  const badge = (seconds: number): string => {
    const whole = Math.floor(seconds);
    return `${String(Math.floor(whole / 60)).padStart(2, '0')}:${String(whole % 60).padStart(2, '0')}`;
  };

  // ------------------------------------------------------------- overlay lanes
  type LayerClip = { layer: Layer; scene: Scene; lane: number; from: number; to: number };
  const layerClips = $derived.by(() => {
    const items: Omit<LayerClip, 'lane'>[] = [];
    for (const scene of ordered) {
      const base = starts.get(scene.id) ?? 0;
      for (const layer of layersOf(scene)) {
        let start = layer.start;
        let end = layer.end;
        if (
          drag &&
          (drag.kind === 'lmove' || drag.kind === 'lleft' || drag.kind === 'lright') &&
          drag.layerId === layer.id
        ) {
          start = drag.start;
          end = drag.end;
        }
        items.push({ layer, scene, from: base + start, to: base + Math.min(end, lengthOf(scene)) });
      }
    }
    items.sort((a, b) => a.from - b.from || a.to - b.to);
    const laneEnds: number[] = [];
    return items.map((item) => {
      let lane = laneEnds.findIndex((end) => end <= item.from + 1e-6);
      if (lane === -1) lane = laneEnds.length;
      laneEnds[lane] = item.to;
      return { ...item, lane };
    });
  });
  const laneCount = $derived(Math.max(1, ...layerClips.map((c) => c.lane + 1)));

  // ----------------------------------------------------------------- helpers
  const timeAt = (clientX: number): number => {
    const rect = content?.getBoundingClientRect();
    return rect ? (clientX - rect.left) / scale : 0;
  };

  /** Pulls `value` onto the playhead or a clip boundary when it is within a few pixels. */
  function snap(value: number): number {
    const marks = [time];
    let cursor = 0;
    for (const scene of ordered) {
      marks.push(cursor);
      cursor += scene.duration;
      marks.push(cursor);
    }
    let best = value;
    let distance = SNAP_PX / scale;
    for (const mark of marks) {
      if (Math.abs(mark - value) < distance) {
        best = mark;
        distance = Math.abs(mark - value);
      }
    }
    return best;
  }

  function listen(move: (e: PointerEvent) => void, up: (e: PointerEvent) => void) {
    const stop = (e: PointerEvent) => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
      up(e);
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
  }

  // -------------------------------------------------------------------- scrub
  function startScrub(event: PointerEvent) {
    if (event.button !== 0) return;
    event.preventDefault();
    drag = { kind: 'scrub' };
    time = clamp(timeAt(event.clientX), 0, total);
    listen(
      (e) => (time = clamp(timeAt(e.clientX), 0, total)),
      () => (drag = null)
    );
  }

  // ------------------------------------------------------------- scene clips
  function pressClip(event: PointerEvent, scene: Scene) {
    if (event.button !== 0 || locked.video) return; // a locked track lets the press scrub instead
    event.stopPropagation();
    selectedId = scene.id;
    selectedLayerId = null;
    const state = { kind: 'move' as const, id: scene.id, startX: event.clientX, dx: 0, moved: false };
    drag = state;
    listen(
      (e) => {
        const dx = e.clientX - state.startX;
        if (!state.moved && Math.abs(dx) < 4) return;
        state.moved = true;
        drag = { ...state, dx, moved: true };
      },
      (e) => {
        const finished = drag;
        drag = null;
        if (!finished || finished.kind !== 'move' || !finished.moved) return;
        const ids = ordered.map((s) => s.id);
        const target = dropIndex(timeAt(e.clientX), scene.id);
        const without = ids.filter((id) => id !== scene.id);
        without.splice(target, 0, scene.id);
        if (without.some((id, i) => id !== ids[i])) onreorder(without);
      }
    );
  }

  /**
   * Where a dragged clip would land: after every other clip whose middle is left
   * of the pointer. Both are measured on the timeline as it is drawn (the
   * dragged clip still occupying its slot), so what you point at is what you get.
   */
  function dropIndex(at: number, movingId: string): number {
    let index = 0;
    let cursor = 0;
    for (const scene of ordered) {
      const middle = cursor + scene.duration / 2;
      cursor += scene.duration;
      if (scene.id !== movingId && middle < at) index += 1;
    }
    return index;
  }

  /** Time of the line shown where the dragged clip would be dropped. */
  const indicatorAt = $derived.by(() => {
    if (!drag || drag.kind !== 'move' || !drag.moved) return null;
    const movingId = drag.id;
    const index = dropIndex(timeAt(drag.startX + drag.dx), movingId);
    const others = ordered.filter((scene) => scene.id !== movingId);
    if (!others.length) return null;
    const target = others[index];
    if (target) return starts.get(target.id) ?? 0;
    const last = others[others.length - 1];
    return (starts.get(last.id) ?? 0) + last.duration;
  });

  function pressEdge(event: PointerEvent, scene: Scene, edge: 'left' | 'right') {
    if (event.button !== 0 || locked.video) return;
    event.stopPropagation();
    event.preventDefault();
    selectedId = scene.id;
    selectedLayerId = null;
    const begin = starts.get(scene.id) ?? 0;
    const startX = event.clientX;
    drag = { kind: edge, id: scene.id, startX, value: scene.duration };
    listen(
      (e) => {
        const dt = (e.clientX - startX) / scale;
        let value: number;
        if (edge === 'right') {
          value = snap(begin + scene.duration + dt) - begin;
          value = clamp(value, MIN_CLIP, 120);
        } else {
          // Dragging the left edge right removes time from the start of the clip.
          const cut = clamp(dt, 0, scene.duration - MIN_CLIP);
          value = scene.duration - cut;
        }
        drag = { kind: edge, id: scene.id, startX, value: round(value, 2) };
      },
      () => {
        const finished = drag;
        drag = null;
        if (!finished || (finished.kind !== 'left' && finished.kind !== 'right')) return;
        if (Math.abs(finished.value - scene.duration) < 0.02) return;
        if (finished.kind === 'right') onresize(scene.id, finished.value);
        else ontrim(scene.id, round(scene.duration - finished.value, 2), scene.duration);
      }
    );
  }

  // ------------------------------------------------------------ overlay clips
  function pressLayer(event: PointerEvent, clip: LayerClip, mode: 'lmove' | 'lleft' | 'lright') {
    if (event.button !== 0 || locked.title) return;
    event.stopPropagation();
    event.preventDefault();
    const { layer, scene } = clip;
    selectedId = scene.id;
    selectedLayerId = layer.id;
    // Bring the playhead into the layer so the canvas shows what was just selected.
    if (time < clip.from || time >= clip.to) time = clip.from + 0.05;

    const startX = event.clientX;
    const orig = { start: layer.start, end: Math.min(layer.end, scene.duration) };
    drag = { kind: mode, sceneId: scene.id, layerId: layer.id, startX, start: orig.start, end: orig.end, orig };
    listen(
      (e) => {
        const dt = (e.clientX - startX) / scale;
        let start = orig.start;
        let end = orig.end;
        if (mode === 'lmove') {
          const length = orig.end - orig.start;
          start = clamp(orig.start + dt, 0, scene.duration - length);
          end = start + length;
        } else if (mode === 'lleft') {
          start = clamp(orig.start + dt, 0, orig.end - MIN_LAYER);
        } else {
          end = clamp(orig.end + dt, orig.start + MIN_LAYER, scene.duration);
        }
        drag = { kind: mode, sceneId: scene.id, layerId: layer.id, startX, start: round(start), end: round(end), orig };
      },
      () => {
        const finished = drag;
        drag = null;
        if (!finished || !('layerId' in finished)) return;
        if (
          Math.abs(finished.start - orig.start) < 0.02 &&
          Math.abs(finished.end - orig.end) < 0.02
        ) {
          return;
        }
        onlayer(scene.id, layer.id, { start: finished.start, end: finished.end });
      }
    );
  }

  // --------------------------------------------------------------- music clip
  const loops = $derived(
    project.music_url && project.music_duration && project.music_duration > 0.5
      ? Math.floor(total / project.music_duration)
      : 0
  );

  // ----------------------------------------------------------------- view bits
  function wheel(event: WheelEvent) {
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    zoom = clamp(scale * (event.deltaY < 0 ? 1.15 : 1 / 1.15), 2, 600);
  }

  // Keep the playhead in view while it moves (playing, stepping, seeking).
  $effect(() => {
    const x = time * scale;
    if (!scroller || drag) return;
    const left = scroller.scrollLeft;
    const room = viewport - LABEL;
    if (x < left + 8 || x > left + room - 24) {
      scroller.scrollLeft = Math.max(0, x - room * 0.3);
    }
  });

  const rowGap = 4;
  type Flag = 'locked' | 'hidden' | 'muted';
  const tracks = $derived<
    { id: string; name: string; icon: IconName; height: number; flags: Flag[] }[]
  >([
    { id: 'title', name: t('editor.track.title'), icon: 'type', height: ROW.lane * laneCount + (laneCount - 1) * 2, flags: ['locked', 'hidden'] },
    { id: 'video', name: t('editor.track.video'), icon: 'film', height: ROW.video, flags: ['locked', 'hidden', 'muted'] },
    { id: 'voice', name: t('editor.track.voice'), icon: 'mic', height: ROW.voice, flags: ['locked', 'muted'] },
    { id: 'captions', name: t('editor.track.captions'), icon: 'captions', height: ROW.captions, flags: ['locked', 'hidden'] },
    { id: 'music', name: t('editor.track.music'), icon: 'music', height: ROW.music, flags: ['locked', 'muted'] }
  ]);
  const bag = (flag: Flag) => (flag === 'locked' ? locked : flag === 'hidden' ? hidden : muted);
  /** A track that is hidden or muted is dimmed in its lane. */
  const dim = (id: string): boolean => !!(hidden[id] || muted[id]);
  const laneTone = (id: string): string => (dim(id) ? 'opacity-40' : '') + (locked[id] ? ' [&_*]:cursor-not-allowed' : '');
</script>

<section class="flex h-full min-h-0 flex-col bg-slate-950">
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="relative min-h-0 flex-1 overflow-auto"
    bind:this={scroller}
    bind:clientWidth={viewport}
    onwheel={wheel}
  >
    <div class="relative flex" style="width:{LABEL + width}px; min-width:100%">
      <!-- track names (stick to the left while the tracks scroll) -->
      <div
        class="sticky left-0 z-40 flex shrink-0 flex-col border-r border-slate-800 bg-slate-950"
        style="width:{LABEL}px; gap:{rowGap}px"
      >
        <div
          class="sticky top-0 z-50 flex items-center bg-slate-950 px-3 font-mono text-[10px] text-slate-500"
          style="height:{ROW.ruler}px"
        >
          {total.toFixed(1)}s
        </div>
        {#each tracks as track (track.id)}
          <div
            class="flex flex-col justify-center gap-0.5 px-2 {locked[track.id] ? 'text-slate-500' : 'text-slate-300'}"
            style="height:{track.height}px"
          >
            <span class="flex items-center gap-1.5 text-[11px] font-medium">
              <Icon name={track.icon} size={12} />
              {track.name}
            </span>
            <span class="flex items-center gap-0.5">
              {#each track.flags as flag (flag)}
                {@const on = bag(flag)[track.id]}
                {@const names = {
                  locked: [t('editor.track.lock'), t('editor.track.unlock')],
                  hidden: [t('editor.track.hide'), t('editor.track.show')],
                  muted: [t('editor.track.mute'), t('editor.track.unmute')]
                }[flag]}
                <button
                  class="grid h-5 w-5 place-items-center rounded transition hover:bg-slate-800 {on
                    ? 'bg-sun-400/15 text-sun-300'
                    : 'text-slate-500 hover:text-slate-200'}"
                  title={`${on ? names[1] : names[0]}`}
                  aria-label={`${track.name}: ${on ? names[1] : names[0]}`}
                  aria-pressed={on}
                  onclick={() => ontoggle(track.id, flag)}
                >
                  <Icon
                    name={flag === 'locked'
                      ? on ? 'lock' : 'unlock'
                      : flag === 'hidden'
                        ? on ? 'eyeOff' : 'eye'
                        : on ? 'volumeOff' : 'volume'}
                    size={12}
                  />
                </button>
              {/each}
            </span>
          </div>
        {/each}
      </div>

      <!-- tracks -->
      <div class="relative flex flex-col pr-4" style="width:{width}px; gap:{rowGap}px" bind:this={content}>
        <!-- ruler -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="sticky top-0 z-30 cursor-col-resize bg-slate-950 select-none"
          style="height:{ROW.ruler}px"
          onpointerdown={startScrub}
        >
          {#each ticks as tick (tick)}
            <span
              class="pointer-events-none absolute bottom-0 flex h-3/4 flex-col justify-end border-l border-slate-700 pl-1 font-mono text-[10px] text-slate-500"
              style="left:{px(tick)}px">{stamp(tick)}</span
            >
          {/each}
        </div>

        <!-- text and sticker lanes -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="relative rounded-md bg-slate-900/70 {laneTone('title')}"
          style="height:{ROW.lane * laneCount + (laneCount - 1) * 2}px"
          onpointerdown={startScrub}
        >
          {#if !layerClips.length}
            <span class="pointer-events-none absolute inset-0 flex items-center pl-3 text-[11px] text-slate-600">
              {t('editor.track.emptyTitle')}
            </span>
          {/if}
          {#each layerClips as clip (clip.layer.id)}
            {@const active = clip.layer.id === selectedLayerId}
            <div
              class="group absolute overflow-hidden rounded-md bg-[image:var(--sun-gradient)] text-[11px] font-semibold text-sun-950 shadow-sm {active
                ? 'ring-2 ring-white'
                : 'ring-1 ring-black/20'}"
              style="left:{px(clip.from)}px; width:{Math.max(px(clip.to - clip.from), 6)}px; top:{clip.lane *
                (ROW.lane + 2) +
                2}px; height:{ROW.lane - 4}px"
              title={clip.layer.text}
            >
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="flex h-full cursor-grab items-center gap-1 truncate px-1.5 whitespace-nowrap select-none active:cursor-grabbing"
                onpointerdown={(e) => pressLayer(e, clip, 'lmove')}
              >
                {#if clip.layer.type === 'sticker'}
                  <Icon name="smile" size={12} class="shrink-0" />
                {:else}
                  <span class="grid h-4 w-4 shrink-0 place-items-center rounded bg-black/15 text-[10px] font-bold">T</span>
                {/if}
                <span class="truncate">{clip.layer.text}</span>
              </div>
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="absolute inset-y-0 left-0 w-1.5 cursor-ew-resize bg-white/60 opacity-0 transition-opacity group-hover:opacity-100"
                class:opacity-100={active}
                onpointerdown={(e) => pressLayer(e, clip, 'lleft')}
              ></div>
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="absolute inset-y-0 right-0 w-1.5 cursor-ew-resize bg-white/60 opacity-0 transition-opacity group-hover:opacity-100"
                class:opacity-100={active}
                onpointerdown={(e) => pressLayer(e, clip, 'lright')}
              ></div>
            </div>
          {/each}
        </div>

        <!-- video clips: the scenes -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="relative rounded-md bg-slate-900/70 {laneTone('video')}"
          style="height:{ROW.video}px"
          onpointerdown={startScrub}
        >
          {#each ordered as scene (scene.id)}
            {@const moving = drag?.kind === 'move' && drag.id === scene.id && drag.moved}
            {@const selected = scene.id === selectedId}
            <div
              class="group absolute top-1 bottom-1 overflow-hidden rounded-md bg-slate-700 shadow-sm {selected
                ? 'ring-2 ring-sun-400'
                : 'ring-1 ring-white/10'}"
              class:opacity-60={moving}
              class:z-10={moving}
              style="left:{px(starts.get(scene.id) ?? 0)}px; width:{Math.max(
                px(lengthOf(scene)),
                8
              )}px; transform:translateX({moving && drag?.kind === 'move' ? drag.dx : 0}px)"
              title={scene.on_screen_text ?? scene.narration.slice(0, 80)}
            >
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="relative h-full cursor-grab select-none active:cursor-grabbing"
                onpointerdown={(e) => pressClip(e, scene)}
              >
                {#if scene.image_url}
                  <!-- a filmstrip: the picture repeated along the clip -->
                  <div
                    class="absolute inset-0 bg-repeat-x opacity-90"
                    style="background-image:url('{scene.image_url}'); background-size:auto 100%"
                  ></div>
                {:else if scene.video_url}
                  <div class="pointer-events-none absolute inset-0 flex">
                    {#each Array.from({ length: clamp(Math.ceil(px(lengthOf(scene)) / 96), 1, 8) }, (_, n) => n) as n (n)}
                      <!-- svelte-ignore a11y_media_has_caption -->
                      <video
                        src={`${scene.video_url}#t=${0.1 + n * 0.5}`}
                        preload="metadata"
                        muted
                        class="h-full min-w-0 flex-1 object-cover opacity-90"
                      ></video>
                    {/each}
                  </div>
                {:else}
                  <div
                    class="absolute inset-0"
                    style="background:linear-gradient(135deg, hsl({(scene.scene_number * 47) % 360} 38% 28%), hsl({(scene.scene_number * 47 + 40) % 360} 34% 15%))"
                  ></div>
                  {#if px(lengthOf(scene)) > 90 && scene.on_screen_text}
                    <span class="absolute inset-x-2 top-1.5 line-clamp-1 text-[11px] leading-tight font-semibold text-white/85">{scene.on_screen_text}</span>
                  {/if}
                {/if}
                <div class="absolute inset-x-0 bottom-0 h-7 bg-gradient-to-t from-black/70 to-transparent"></div>
                <span class="absolute bottom-1 left-1 inline-flex items-center gap-1 rounded bg-black/55 px-1.5 py-0.5 text-[10px] font-medium text-white/95">
                  {scene.scene_number} · {lengthOf(scene).toFixed(1)}s
                  {#if scene.video_url}<Icon name="video" size={10} />{/if}
                </span>
              </div>
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="absolute inset-y-0 left-0 w-2 cursor-ew-resize bg-white/70 opacity-0 transition-opacity group-hover:opacity-100"
                class:opacity-100={selected}
                title={t('editor.track.trimStart')}
                onpointerdown={(e) => pressEdge(e, scene, 'left')}
              ></div>
              <!-- svelte-ignore a11y_no_static_element_interactions -->
              <div
                class="absolute inset-y-0 right-0 w-2 cursor-ew-resize bg-white/70 opacity-0 transition-opacity group-hover:opacity-100"
                class:opacity-100={selected}
                title={t('editor.track.trimEnd')}
                onpointerdown={(e) => pressEdge(e, scene, 'right')}
              ></div>
            </div>
          {/each}
          {#if indicatorAt !== null}
            <div
              class="pointer-events-none absolute inset-y-0 z-20 w-0.5 rounded bg-sun-300"
              style="left:{px(indicatorAt)}px"
            ></div>
          {/if}
        </div>

        <!-- voice -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="relative rounded-md bg-slate-900/70 {laneTone('voice')}"
          style="height:{ROW.voice}px"
          onpointerdown={startScrub}
        >
          {#each ordered.filter((s) => s.audio_url) as scene (scene.id)}
            {@const volume = typeof scene.settings?.voice_volume === 'number' ? scene.settings.voice_volume : 1}
            <button
              class="absolute top-1 bottom-1 overflow-hidden rounded bg-teal-600/55 px-1.5 text-left text-[10px] font-medium whitespace-nowrap text-teal-50 ring-1 {scene.id === selectedId ? 'ring-teal-200/70' : 'ring-teal-300/20'}"
              style="left:{px(starts.get(scene.id) ?? 0)}px; width:{Math.max(px(lengthOf(scene)), 6)}px"
              title={t('editor.track.narrationTip', { n: scene.scene_number, pct: Math.round(volume * 100) })}
              onpointerdown={(e) => {
                if (locked.voice) return;
                e.stopPropagation();
                selectedId = scene.id;
                selectedLayerId = null;
              }}
            >
              {#if px(lengthOf(scene)) > 24}
                <svg class="pointer-events-none absolute inset-x-0.5 inset-y-0.5 h-[calc(100%-4px)] w-[calc(100%-4px)]" viewBox="0 0 {bars(scene.id, px(lengthOf(scene))).length} 10" preserveAspectRatio="none" aria-hidden="true">
                  {#each bars(scene.id, px(lengthOf(scene))) as h, i (i)}
                    <rect x={i + 0.2} y={5 - h / 2} width="0.6" height={h} rx="0.3" fill="rgb(204 251 241 / {0.4 + volume * 0.45})" />
                  {/each}
                </svg>
              {/if}
              {#if px(lengthOf(scene)) > 70 && volume < 1}<span class="relative">{Math.round(volume * 100)}%</span>{/if}
            </button>
          {/each}
        </div>

        <!-- captions (edited in the scene panel) -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="relative rounded-md bg-slate-900/70 {laneTone('captions')}"
          style="height:{ROW.captions}px"
          onpointerdown={startScrub}
        >
          {#each ordered as scene (scene.id)}
            {#each scene.captions as caption (caption.id)}
              {@const begin = (starts.get(scene.id) ?? 0) + caption.start_time}
              {#if caption.start_time < lengthOf(scene)}
                <button
                  class="absolute top-1 bottom-1 cursor-pointer overflow-hidden rounded-sm px-1 text-left text-[9px] whitespace-nowrap text-slate-200 transition hover:bg-slate-600 {time >=
                    begin && time < (starts.get(scene.id) ?? 0) + Math.min(caption.end_time, lengthOf(scene))
                    ? 'bg-sun-500/45 text-sun-50'
                    : 'bg-slate-700/80'}"
                  style="left:{px(begin)}px; width:{Math.max(
                    px(Math.min(caption.end_time, lengthOf(scene)) - caption.start_time),
                    3
                  )}px"
                  title={t('editor.track.captionTip', { text: caption.text })}
                  onpointerdown={(e) => {
                    if (locked.captions) return;
                    e.stopPropagation();
                    oncaption(scene.id, caption.start_time);
                  }}
                >
                  {#if px(Math.min(caption.end_time, lengthOf(scene)) - caption.start_time) > 44}{caption.text}{/if}
                </button>
              {/if}
            {/each}
          {/each}
        </div>

        <!-- music -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div
          class="relative overflow-hidden rounded-md bg-slate-900/70 {laneTone('music')}"
          style="height:{ROW.music}px"
          onpointerdown={startScrub}
        >
          {#if project.music.enabled && project.music.volume > 0}
            <div
              class="pointer-events-none absolute top-1 bottom-1 left-0 overflow-hidden rounded bg-teal-600/55 px-2 text-[10px] leading-5 font-medium whitespace-nowrap text-teal-50 ring-1 ring-teal-300/20"
              style="width:{px(total)}px"
            >
              {#if px(total) > 24}
                <svg class="absolute inset-x-0.5 inset-y-0.5 h-[calc(100%-4px)] w-[calc(100%-4px)]" viewBox="0 0 {bars('music', px(total)).length} 10" preserveAspectRatio="none" aria-hidden="true">
                  {#each bars('music', px(total)) as h, i (i)}
                    <rect x={i + 0.2} y={5 - h / 2} width="0.6" height={h} rx="0.3" fill="rgb(204 251 241 / 0.45)" />
                  {/each}
                </svg>
              {/if}
              <span class="relative">♪ {project.music_name ?? t('editor.track.builtIn')} · {Math.round(project.music.volume * 100)}%</span>
            </div>
            {#each Array.from({ length: loops }, (_, i) => i + 1) as n (n)}
              <div
                class="pointer-events-none absolute top-1 bottom-1 w-px bg-white/40"
                style="left:{px(n * (project.music_duration ?? 0))}px"
              ></div>
            {/each}
          {:else}
            <span class="pointer-events-none absolute inset-0 flex items-center pl-3 text-[11px] text-slate-600">
              {t('editor.track.musicOff')}
            </span>
          {/if}
        </div>

        <!-- playhead -->
        <div
          class="pointer-events-none absolute top-0 bottom-0 z-40 w-0.5 -translate-x-1/2 bg-sun-400"
          style="left:{px(time)}px"
        >
          <span
            class="absolute top-1 left-1/2 -translate-x-1/2 rounded bg-sun-400 px-1.5 py-0.5 font-mono text-[10px] leading-none font-semibold text-sun-950 tabular-nums"
            >{badge(time)}</span
          >
        </div>
      </div>
    </div>
  </div>
</section>
