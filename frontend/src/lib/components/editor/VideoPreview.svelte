<script lang="ts">
  /** Presenter-led editor preview with timed emphasis text and narration. */
  import EducationalAvatar from '$lib/components/editor/EducationalAvatar.svelte';
  import type { Scene } from '$lib/types/api';

  type StoryPhase = 'hook' | 'setup' | 'rising' | 'twist' | 'climax' | 'payoff';
  const phaseThemes: Record<StoryPhase, { label: string; base: string; glow: string; accent: string }> = {
    hook: { label: 'HOOK', base: '#2a0b12', glow: '#f97316', accent: '#fb923c' },
    setup: { label: 'SETUP', base: '#10172f', glow: '#3b82f6', accent: '#60a5fa' },
    rising: { label: 'RISING ACTION', base: '#062d2b', glow: '#14b8a6', accent: '#2dd4bf' },
    twist: { label: 'TWIST', base: '#2e1065', glow: '#a855f7', accent: '#c084fc' },
    climax: { label: 'CLIMAX', base: '#3f0a0a', glow: '#ef4444', accent: '#fb7185' },
    payoff: { label: 'PAYOFF', base: '#392008', glow: '#f59e0b', accent: '#fbbf24' }
  };

  function storyPhase(sceneNumber: number, sceneCount: number): StoryPhase {
    if (sceneNumber <= 1) return 'hook';
    const progress = (sceneNumber - 1) / Math.max(1, sceneCount - 1);
    if (progress < 0.28) return 'setup';
    if (progress < 0.58) return 'rising';
    if (progress < 0.76) return 'twist';
    if (progress < 0.92) return 'climax';
    return 'payoff';
  }

  let {
    scenes,
    projectTitle = 'Khmer Story Studio',
    aspectRatio = '16:9',
    language = 'km',
    time = $bindable(0),
    selectedId = $bindable<string | null>(null)
  }: {
    scenes: Scene[];
    projectTitle?: string;
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
    scenes.find((scene) => time >= scene.start_time && time < scene.start_time + scene.duration) ?? scenes.at(-1) ?? null
  );
  const localTime = $derived(current ? time - current.start_time : 0);
  const caption = $derived(current?.captions.find((c) => localTime >= c.start_time && localTime < c.end_time) ?? null);
  const isKhmer = $derived((current?.language ?? language).startsWith('km'));
  const portrait = $derived(aspectRatio === '9:16');
  const phase = $derived(current ? storyPhase(current.scene_number, scenes.length) : 'hook');
  const theme = $derived(phaseThemes[phase]);
  const mirror = $derived(!portrait && !!current && current.scene_number % 2 === 0);
  const ratioClass = $derived(aspectRatio === '9:16' ? 'aspect-[9/16] max-h-[70vh]' : aspectRatio === '1:1' ? 'aspect-square' : 'aspect-video');
  const popupStart = $derived(current ? Math.min(0.8, current.duration * 0.18) : 0);
  const popupEnd = $derived(current ? Math.min(current.duration - 0.2, popupStart + 4.5) : 0);
  const popupOpacity = $derived(
    !current?.on_screen_text || localTime < popupStart || localTime > popupEnd
      ? 0
      : Math.min(1, (localTime - popupStart) / 0.25, (popupEnd - localTime) / 0.3)
  );
  const popupScale = $derived(0.78 + 0.22 * Math.min(1, Math.max(0, (localTime - popupStart) / 0.32)));

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
    } else audio.pause();
  });

  $effect(() => {
    if (current && selectedId !== current.id && playing) selectedId = current.id;
  });
</script>

<div class="flex flex-col gap-3">
  <div
    class="relative w-full overflow-hidden rounded-xl border border-slate-800 bg-black {ratioClass}"
    style={`background: radial-gradient(circle at 26% 35%, ${theme.glow}55, transparent 32%), radial-gradient(circle at 80% 20%, ${theme.accent}33, transparent 28%), linear-gradient(125deg, #08070d 0%, ${theme.base} 55%, ${current?.background_color ?? '#0b0d12'} 125%)`}
  >
    <div class="absolute inset-0 opacity-70" style={`background:${phase === 'climax' ? 'repeating-conic-gradient(from 210deg at 70% 48%,rgba(239,68,68,.16) 0deg 7deg,transparent 7deg 18deg)' : phase === 'twist' ? 'repeating-linear-gradient(135deg,rgba(168,85,247,.11) 0 3%,transparent 3% 10%)' : 'repeating-linear-gradient(90deg,rgba(255,255,255,.035) 0 5.5%,rgba(2,6,23,.22) 5.5% 10.5%,rgba(255,255,255,.025) 10.5% 16%)'}`}></div>

    {#if current}
      <div class="absolute top-[4.5%] right-[5%] left-[5%] z-10 flex items-center justify-between text-[clamp(.42rem,1.1vw,.8rem)] font-bold tracking-[.08em] text-slate-300">
        <span>✦ KHMER STORY · {projectTitle.toUpperCase()}</span>
        <span style={`color:${theme.accent}`}>SCENE {current.scene_number} · {theme.label}</span>
      </div>

      <div class="absolute top-[19%] right-[9%] aspect-square w-[7%] rounded-full border-2" style={`border-color:${theme.accent}88;background:${theme.glow}18;box-shadow:0 0 35px ${theme.glow}44`}></div>
      <div class="absolute top-[39%] right-[23%] aspect-square w-[10%] rounded-full border-2" style={`border-color:${theme.accent}66;background:${theme.glow}12;box-shadow:0 0 45px ${theme.glow}33`}></div>
      <div class="absolute top-[58%] right-[8%] aspect-square w-[12%] rounded-full border-2" style={`border-color:${theme.accent}55;background:${theme.glow}10;box-shadow:0 0 55px ${theme.glow}28`}></div>

      <div class="absolute z-10 drop-shadow-2xl" style={portrait ? 'left:12%;top:25%;width:76%;height:67%' : mirror ? 'left:48%;top:15%;width:46%;height:80%' : 'left:8%;top:15%;width:46%;height:80%'}>
        <EducationalAvatar speaking={playing && !!current.audio_url} mood={phase} />
      </div>

      {#if current.on_screen_text && popupOpacity > 0}
        <div
          class="absolute z-20 rounded-full border border-white/30 bg-gradient-to-br from-amber-500 to-orange-600 px-[4%] py-[2.5%] font-black text-orange-50 shadow-[0_20px_55px_rgba(234,88,12,.3)]"
          class:km={isKhmer}
          style={`left:${portrait ? '7%' : mirror ? '8%' : '50%'};right:${portrait ? '7%' : mirror ? '50%' : '8%'};top:${portrait ? '13%' : '31%'};opacity:${popupOpacity};transform:scale(${popupScale});transform-origin:${portrait ? 'center' : mirror ? 'right center' : 'left center'};text-align:${portrait ? 'center' : mirror ? 'right' : 'left'};font-size:clamp(.8rem,3.3vw,2.5rem);line-height:${isKhmer ? '1.7' : '1.15'};background:linear-gradient(115deg,${theme.glow}f2,${theme.base}f2);box-shadow:0 20px 55px ${theme.glow}55`}
        >
          {current.on_screen_text}
        </div>
      {/if}

      <div class="absolute right-0 bottom-0 left-0 z-20 h-[10%] border-t-2 border-orange-400 bg-gradient-to-b from-orange-800 to-[#431407] shadow-[0_-12px_30px_rgba(2,6,23,.5)]"></div>

      {#if caption}
        <div class="absolute inset-x-[6%] bottom-[2.5%] z-30 text-center">
          <span class="inline-block rounded-lg border border-white/10 bg-slate-950/90 px-3 py-1.5 font-semibold text-white shadow-xl" class:km={isKhmer} style="font-size: clamp(.75rem, 2vw, 1.15rem)">
            {caption.text}
          </span>
        </div>
      {/if}
    {:else}
      <div class="flex h-full items-center justify-center text-sm text-slate-500">No scenes yet</div>
    {/if}
  </div>

  <div class="flex items-center gap-3">
    <button class="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium hover:bg-indigo-500" onclick={togglePlay} disabled={!scenes.length}>
      {playing ? 'Pause' : 'Play'}
    </button>
    <input type="range" min="0" max={Math.max(total, 0.1)} step="0.05" bind:value={time} class="flex-1 accent-indigo-500" aria-label="Playhead" />
    <span class="w-24 text-right font-mono text-xs text-slate-400">{time.toFixed(1)}s / {total.toFixed(1)}s</span>
  </div>
</div>
