<script lang="ts">
  /**
   * Four-track timeline: video, voice, captions, music.
   *
   * Clip positions are derived from scene start_time/duration, which the backend
   * computes - the UI never invents timing of its own.
   */
  import TimelineClip from '$lib/components/editor/TimelineClip.svelte';
  import TimelineTrack from '$lib/components/editor/TimelineTrack.svelte';
  import type { Scene } from '$lib/types/api';

  let {
    scenes,
    time = $bindable(0),
    selectedId = $bindable<string | null>(null)
  }: { scenes: Scene[]; time?: number; selectedId?: string | null } = $props();

  const total = $derived(Math.max(scenes.reduce((sum, s) => sum + s.duration, 0), 0.001));
  const pct = (value: number) => (value / total) * 100;

  function seek(event: MouseEvent) {
    const target = event.currentTarget as HTMLElement;
    const rect = target.getBoundingClientRect();
    time = ((event.clientX - rect.left) / rect.width) * total;
  }
</script>

<section class="flex flex-col gap-2 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
  <div class="flex items-center justify-between">
    <h3 class="text-xs font-semibold tracking-wide text-slate-400 uppercase">Timeline</h3>
    <span class="font-mono text-xs text-slate-500">{total.toFixed(1)}s</span>
  </div>

  <!-- svelte-ignore a11y_no_static_element_interactions, a11y_click_events_have_key_events -->
  <div class="relative flex flex-col gap-1.5" onclick={seek}>
    <TimelineTrack name="Video">
      {#each scenes as scene (scene.id)}
        <TimelineClip
          label={`#${scene.scene_number}`}
          left={pct(scene.start_time)}
          width={pct(scene.duration)}
          tone={scene.image_url ? 'bg-indigo-600/80' : 'bg-slate-700/80'}
          selected={scene.id === selectedId}
          title={scene.on_screen_text ?? scene.narration.slice(0, 60)}
          onclick={() => (selectedId = scene.id)}
        />
      {/each}
    </TimelineTrack>

    <TimelineTrack name="Voice">
      {#each scenes.filter((s) => s.audio_url) as scene (scene.id)}
        <TimelineClip
          label="voice"
          left={pct(scene.start_time)}
          width={pct(scene.duration)}
          tone="bg-emerald-700/80"
          title={`scene ${scene.scene_number} narration`}
        />
      {/each}
    </TimelineTrack>

    <TimelineTrack name="Captions">
      {#each scenes as scene (scene.id)}
        {#each scene.captions as caption (caption.id)}
          <TimelineClip
            label={caption.text.slice(0, 12)}
            left={pct(scene.start_time + caption.start_time)}
            width={pct(Math.max(caption.end_time - caption.start_time, 0.05))}
            tone="bg-sky-700/80"
            title={caption.text}
          />
        {/each}
      {/each}
    </TimelineTrack>

    <TimelineTrack name="Music">
      <span class="absolute inset-0 flex items-center justify-center text-[10px] text-slate-600">
        no music track yet
      </span>
    </TimelineTrack>

    <!-- playhead -->
    <div
      class="pointer-events-none absolute top-0 bottom-0 w-px bg-red-400"
      style={`left: calc(4rem + 0.5rem + ${pct(time)}% * 0.995)`}
    ></div>
  </div>
</section>
