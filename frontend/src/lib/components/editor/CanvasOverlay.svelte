<script lang="ts">
  /**
   * Direct manipulation of text and sticker layers on the preview.
   *
   * The Remotion player draws the layers; this sits on top of it, draws nothing
   * visible except the selection frame and handles, and turns pointer movement
   * into edits:
   *
   *   drag the layer        move it (snaps to the frame's centre lines)
   *   drag the corner dot   resize it (font size)
   *   drag the top dot      rotate it (snaps every 15 degrees)
   *
   * The overlay is laid out in COMPOSITION pixels and scaled to the player, and
   * uses the renderer's own `layerTextStyle`, so each box is exactly where the
   * text will be in the exported video.
   *
   * While a gesture is in progress `ondraft` reports the live values (the
   * preview redraws from them) and ONE `oncommit` reports the result at the end.
   */
  import { layerPlacement, layerTextStyle } from '$renderer/layerStyle';
  import { clamp, cssText, round, toRenderLayer } from '$lib/editor/layers';
  import type { Layer } from '$lib/types/api';

  type Patch = Partial<Pick<Layer, 'x' | 'y' | 'font_size' | 'rotation'>>;

  let {
    layers,
    selectedLayerId = $bindable<string | null>(null),
    compWidth,
    compHeight,
    language,
    ondraft,
    oncommit,
    onedit
  }: {
    /** The layers on screen at the playhead. */
    layers: Layer[];
    selectedLayerId?: string | null;
    compWidth: number;
    compHeight: number;
    language: string;
    ondraft: (layerId: string, patch: Patch | null) => void;
    oncommit: (layerId: string, patch: Patch) => void;
    onedit: (layerId: string) => void;
  } = $props();

  let box = $state(0);
  const k = $derived(box > 0 ? box / compWidth : 1);

  let draft = $state<{ id: string; patch: Patch } | null>(null);
  let guides = $state({ x: false, y: false });

  const live = (layer: Layer): Layer =>
    draft && draft.id === layer.id ? { ...layer, ...draft.patch } : layer;

  function setDraft(id: string, patch: Patch) {
    draft = { id, patch };
    ondraft(id, patch);
  }

  function finish(id: string, patch: Patch | null) {
    draft = null;
    guides = { x: false, y: false };
    ondraft(id, null);
    if (patch) oncommit(id, patch);
  }

  function track(move: (e: PointerEvent) => void, up: () => void) {
    const stop = () => {
      window.removeEventListener('pointermove', move);
      window.removeEventListener('pointerup', stop);
      window.removeEventListener('pointercancel', stop);
      up();
    };
    window.addEventListener('pointermove', move);
    window.addEventListener('pointerup', stop);
    window.addEventListener('pointercancel', stop);
  }

  /** Pointer down on the layer: select, and move it once the pointer travels. */
  function pressMove(event: PointerEvent, layer: Layer) {
    if (event.button !== 0) return;
    event.stopPropagation();
    event.preventDefault();
    selectedLayerId = layer.id;
    const startX = event.clientX;
    const startY = event.clientY;
    let patch: Patch | null = null;
    track(
      (e) => {
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;
        if (!patch && Math.hypot(dx, dy) < 3) return;
        let x = clamp(layer.x + (dx / k / compWidth) * 100, 0, 100);
        let y = clamp(layer.y + (dy / k / compHeight) * 100, 0, 100);
        const snapX = Math.abs(x - 50) < 1.2;
        const snapY = Math.abs(y - 50) < 1.2;
        if (snapX) x = 50;
        if (snapY) y = 50;
        guides = { x: snapX, y: snapY };
        patch = { x: round(x, 2), y: round(y, 2) };
        setDraft(layer.id, patch);
      },
      () => finish(layer.id, patch)
    );
  }

  function centreOf(target: HTMLElement): { x: number; y: number } {
    const rect = (target.closest('[data-layer]') as HTMLElement).getBoundingClientRect();
    return { x: rect.left + rect.width / 2, y: rect.top + rect.height / 2 };
  }

  function pressResize(event: PointerEvent, layer: Layer) {
    if (event.button !== 0) return;
    event.stopPropagation();
    event.preventDefault();
    const centre = centreOf(event.currentTarget as HTMLElement);
    const startDistance = Math.max(8, Math.hypot(event.clientX - centre.x, event.clientY - centre.y));
    let patch: Patch | null = null;
    track(
      (e) => {
        const distance = Math.hypot(e.clientX - centre.x, e.clientY - centre.y);
        patch = { font_size: round(clamp((layer.font_size * distance) / startDistance, 1, 60), 2) };
        setDraft(layer.id, patch);
      },
      () => finish(layer.id, patch)
    );
  }

  function pressRotate(event: PointerEvent, layer: Layer) {
    if (event.button !== 0) return;
    event.stopPropagation();
    event.preventDefault();
    const centre = centreOf(event.currentTarget as HTMLElement);
    let patch: Patch | null = null;
    track(
      (e) => {
        let degrees = (Math.atan2(e.clientY - centre.y, e.clientX - centre.x) * 180) / Math.PI + 90;
        if (degrees > 180) degrees -= 360;
        const nearest = Math.round(degrees / 15) * 15;
        if (Math.abs(degrees - nearest) < 4) degrees = nearest;
        patch = { rotation: round(clamp(degrees, -180, 180), 1) };
        setDraft(layer.id, patch);
      },
      () => finish(layer.id, patch)
    );
  }

  const dot = $derived(Math.max(10, 14 / k));
</script>

<div class="pointer-events-none absolute inset-0 overflow-hidden" bind:clientWidth={box}>
  <div
    class="absolute top-0 left-0"
    style="width:{compWidth}px; height:{compHeight}px; transform:scale({k}); transform-origin:0 0"
  >
    {#if selectedLayerId}
      <!-- Clicking anywhere else deselects, instead of toggling playback. -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="pointer-events-auto absolute inset-0"
        onpointerdown={(e) => {
          e.stopPropagation();
          selectedLayerId = null;
        }}
      ></div>
    {/if}

    {#if guides.x}
      <div class="absolute top-0 bottom-0 left-1/2 bg-pink-400/80" style="width:{2 / k}px"></div>
    {/if}
    {#if guides.y}
      <div class="absolute top-1/2 right-0 left-0 bg-pink-400/80" style="height:{2 / k}px"></div>
    {/if}

    {#each layers as source (source.id)}
      {@const layer = live(source)}
      {@const selected = layer.id === selectedLayerId}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        data-layer={layer.id}
        class="pointer-events-auto cursor-move"
        style="position:absolute; left:{layer.x}%; top:{layer.y}%; transform:translate(-50%,-50%) rotate({layer.rotation}deg)"
        onpointerdown={(e) => pressMove(e, source)}
        ondblclick={() => onedit(layer.id)}
      >
        <!-- The player already draws the text; this copy is invisible and only gives the box. -->
        <div
          style="{cssText(layerTextStyle(toRenderLayer(layer), compWidth, compHeight, language))}; color:transparent; text-shadow:none; background:transparent; outline:{selected
            ? `${2 / k}px solid #ffa733`
            : `${1 / k}px dashed rgba(255,255,255,.35)`}; outline-offset:{4 / k}px"
        >
          {layer.text}
        </div>
        {#if selected}
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            class="absolute cursor-nwse-resize rounded-full border-sun-500 bg-white"
            style="width:{dot}px; height:{dot}px; right:{-dot / 2 - 4 / k}px; bottom:{-dot / 2 -
              4 / k}px; border-width:{2 / k}px"
            title="Resize"
            onpointerdown={(e) => pressResize(e, source)}
          ></div>
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div
            class="absolute cursor-grab rounded-full border-sun-500 bg-white"
            style="width:{dot}px; height:{dot}px; left:calc(50% - {dot / 2}px); top:{-dot * 2.4}px; border-width:{2 / k}px"
            title="Rotate"
            onpointerdown={(e) => pressRotate(e, source)}
          ></div>
          <div
            class="pointer-events-none absolute bg-sun-500"
            style="left:calc(50% - {1 / k}px); width:{2 / k}px; top:{-dot * 1.4}px; height:{dot * 1.4 - 4 / k}px"
          ></div>
        {/if}
      </div>
    {/each}
  </div>
</div>
