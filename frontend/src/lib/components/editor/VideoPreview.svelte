<script lang="ts">
  /**
   * Scene preview with a real playhead.
   *
   * It is NOT a video player: nothing is rendered yet while you edit. It draws
   * the scene the playhead is on - image, title, the caption active at that
   * moment - and plays that scene's narration audio, which is enough to judge
   * timing before committing to a render.
   */
  import type { Scene } from '$lib/types/api';

  let {
    scenes,
    aspectRatio = '16:9',
    language = 'en',
    time = $bindable(0),
    selectedId = $bindable<string | null>(null)
  }: {
    scenes: Scene[];
    aspectRatio?: string;
    language?: string;
    time?: number;
    selectedId?: string | null;
  } = $props();

  let playing = $state(false);
  let audio: HTMLAudioElement | null = null;
  let raf = 0;
  let lastTick = 0;

  const total = $derived(scenes.reduce((sum, scene) => sum + scene.duration, 0));
  const current = $derived(
    scenes.find((scene) => time >= scene.start_time && time < scene.start_time + scene.duration) ??
      scenes.at(-1) ??
      null
  );
  const localTime = $derived(current ? time - current.start_time : 0);
  const caption = $derived(
    current?.captions.find((c) => localTime >= c.start_time && localTime < c.end_time) ?? null
  );
  const isKhmer = $derived((current?.language ?? language).startsWith('km'));
  const ratioClass = $derived(
    aspectRatio === '9:16' ? 'aspect-[9/16] max-h-[70vh]' : aspectRatio === '1:1' ? 'aspect-square' : 'aspect-video'
  );

  function tick(now: number) {
    if (!playing) return;
    const delta = (now - lastTick) / 1000;
    lastTick = now;
    time = Math.min(time + delta, total);
    if (time >= total) playing = false;
    else raf = requestAnimationFrame(tick);
  }

  function togglePlay() {
    playing = !playing;
    if (playing) {
      lastTick = performance.now();
      raf = requestAnimationFrame(tick);
    } else {
      cancelAnimationFrame(raf);
      audio?.pause();
    }
  }

  // Keep the narration audio in sync with the playhead.
  $effect(() => {
    if (!current?.audio_url) {
      audio?.pause();
      return;
    }
    if (!audio || audio.dataset.sceneId !== current.id) {
      audio?.pause();
      audio = new Audio(current.audio_url);
      audio.dataset.sceneId = current.id;
    }
    if (playing) {
      if (Math.abs(audio.currentTime - localTime) > 0.35) audio.currentTime = localTime;
      void audio.play().catch(() => undefined);
    } else {
      audio.pause();
    }
  });

  $effect(() => {
    if (current && selectedId !== current.id && playing) selectedId = current.id;
  });
</script>

<div class="flex flex-col gap-3">
  <div
    class="relative w-full overflow-hidden rounded-xl border border-slate-800 bg-black {ratioClass}"
    style={`background-color: ${current?.background_color ?? '#000'}`}
  >
    {#if current?.image_url}
      <img src={current.image_url} alt="" class="h-full w-full object-cover" />
      <div
        class="absolute inset-0"
        style="background: linear-gradient(180deg, rgba(0,0,0,.35) 0%, rgba(0,0,0,.1) 45%, rgba(0,0,0,.55) 100%)"
      ></div>
    {/if}

    {#if current?.on_screen_text}
      <div class="absolute inset-0 flex items-center justify-center px-[10%] text-center">
        <h2
          class="font-bold text-white drop-shadow-[0_4px_18px_rgba(0,0,0,.8)]"
          class:km={isKhmer}
          style="font-size: clamp(1.25rem, 4.2vw, 3rem)"
        >
          {current.on_screen_text}
        </h2>
      </div>
    {/if}

    {#if caption}
      <div class="absolute inset-x-[8%] bottom-[7%] text-center">
        <span
          class="inline-block rounded-lg bg-black/70 px-3 py-1.5 text-white"
          class:km={isKhmer}
          style="font-size: clamp(.75rem, 2vw, 1.15rem)"
        >
          {caption.text}
        </span>
      </div>
    {/if}

    {#if !current}
      <div class="flex h-full items-center justify-center text-sm text-slate-500">
        No scenes yet
      </div>
    {/if}
  </div>

  <div class="flex items-center gap-3">
    <button
      class="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium hover:bg-indigo-500"
      onclick={togglePlay}
      disabled={!scenes.length}
    >
      {playing ? 'Pause' : 'Play'}
    </button>
    <input
      type="range"
      min="0"
      max={Math.max(total, 0.1)}
      step="0.05"
      bind:value={time}
      class="flex-1 accent-indigo-500"
      aria-label="Playhead"
    />
    <span class="w-24 text-right font-mono text-xs text-slate-400">
      {time.toFixed(1)}s / {total.toFixed(1)}s
    </span>
  </div>
</div>
