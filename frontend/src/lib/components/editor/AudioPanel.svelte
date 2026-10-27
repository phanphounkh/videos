<script lang="ts">
  /** Sound: this scene's voice and clip volume, and the video's music track. */
  import Button from '$lib/components/ui/Button.svelte';
  import Field from '$lib/components/ui/Field.svelte';
  import { t } from '$lib/i18n/index.svelte';
  import type { MusicSettings, Project, Scene } from '$lib/types/api';

  let {
    scene,
    project,
    busy = false,
    onsettings,
    onuploadMusic,
    onremoveMusic,
    onmusic
  }: {
    scene: Scene | null;
    project: Project;
    busy?: boolean;
    onsettings: (sceneId: string, patch: Record<string, unknown>) => void;
    onuploadMusic: (file: File) => void;
    onremoveMusic: () => void;
    onmusic: (patch: Partial<MusicSettings>) => void;
  } = $props();

  const num = (value: unknown, fallback: number): number =>
    typeof value === 'number' && Number.isFinite(value) ? value : fallback;

  const voice = $derived(num(scene?.settings?.voice_volume, 1));
  const clip = $derived(num(scene?.settings?.clip_volume, 0));

  // Sliders move freely and save on release.
  let voiceDraft = $state(1);
  let clipDraft = $state(0);
  let volumeDraft = $state(1);
  let fadeInDraft = $state(0.4);
  let fadeOutDraft = $state(1);
  $effect(() => void (voiceDraft = voice));
  $effect(() => void (clipDraft = clip));
  $effect(() => void (volumeDraft = project.music.volume));
  $effect(() => void (fadeInDraft = project.music.fade_in));
  $effect(() => void (fadeOutDraft = project.music.fade_out));

  let musicFile = $state<HTMLInputElement>();
  const range = 'w-full accent-sun-500';
  const pct = (value: number) => `${Math.round(value * 100)}%`;
</script>

<div class="flex flex-col gap-4">
  {#if scene}
    <section class="flex flex-col gap-3">
      <h3 class="section-title">
        {t('editor.audio.sceneSound', { n: scene.scene_number })}
      </h3>
      <Field
        label={t('editor.audio.voice', { pct: pct(voiceDraft) })}
        hint={scene.audio_url ? undefined : t('editor.audio.noVoice')}
      >
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          bind:value={voiceDraft}
          disabled={!scene.audio_url}
          onchange={() => onsettings(scene.id, { voice_volume: voiceDraft === 1 ? null : voiceDraft })}
          class={range}
        />
      </Field>
      {#if scene.video_url}
        <Field label={t('editor.audio.clipSound', { pct: pct(clipDraft) })} hint={t('editor.audio.clipHint')}>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            bind:value={clipDraft}
            onchange={() => onsettings(scene.id, { clip_volume: clipDraft === 0 ? null : clipDraft })}
            class={range}
          />
        </Field>
      {/if}
    </section>
  {/if}

  <section class="flex flex-col gap-3 border-t border-slate-800 pt-4">
    <h3 class="section-title">{t('editor.audio.music')}</h3>

    <label class="flex items-center gap-2 text-sm text-slate-300">
      <input
        type="checkbox"
        checked={project.music.enabled}
        onchange={(e) => onmusic({ enabled: e.currentTarget.checked })}
      />
      {t('editor.audio.bgMusic')}
    </label>

    <p class="text-xs text-slate-400">
      {#if project.music_url}
        ♪ {project.music_name ?? t('editor.audio.yourTrack')}
        {#if project.music_duration}· {t('editor.audio.repeats', { n: project.music_duration.toFixed(0) })}{/if}
      {:else}
        {t('editor.audio.builtIn')}
      {/if}
    </p>
    {#if project.music_url}
      <!-- svelte-ignore a11y_media_has_caption -->
      <audio controls src={project.music_url} class="h-9 w-full"></audio>
    {/if}

    <div class="flex flex-wrap gap-2">
      <Button variant="secondary" size="sm" icon="upload" loading={busy} onclick={() => musicFile?.click()}>
        {project.music_url ? t('editor.audio.replace') : t('editor.audio.upload')}
      </Button>
      {#if project.music_url}
        <Button variant="ghost" size="sm" onclick={onremoveMusic}>{t('editor.audio.useBuiltIn')}</Button>
      {/if}
    </div>
    <input
      bind:this={musicFile}
      type="file"
      accept="audio/mpeg,audio/wav,audio/mp4,audio/x-m4a,audio/ogg,.mp3,.wav,.m4a,.ogg"
      class="hidden"
      onchange={(e) => {
        const file = e.currentTarget.files?.[0];
        e.currentTarget.value = '';
        if (file) onuploadMusic(file);
      }}
    />

    <Field label={t('editor.audio.volume', { pct: pct(volumeDraft) })}>
      <input
        type="range"
        min="0"
        max="1"
        step="0.05"
        bind:value={volumeDraft}
        onchange={() => onmusic({ volume: volumeDraft })}
        class={range}
      />
    </Field>
    <div class="grid grid-cols-2 gap-3">
      <Field label={t('editor.audio.fadeIn', { n: fadeInDraft.toFixed(1) })}>
        <input
          type="range"
          min="0"
          max="10"
          step="0.1"
          bind:value={fadeInDraft}
          onchange={() => onmusic({ fade_in: fadeInDraft })}
          class={range}
        />
      </Field>
      <Field label={t('editor.audio.fadeOut', { n: fadeOutDraft.toFixed(1) })}>
        <input
          type="range"
          min="0"
          max="10"
          step="0.1"
          bind:value={fadeOutDraft}
          onchange={() => onmusic({ fade_out: fadeOutDraft })}
          class={range}
        />
      </Field>
    </div>
    <label class="flex items-center gap-2 text-sm text-slate-300">
      <input
        type="checkbox"
        checked={project.music.duck}
        onchange={(e) => onmusic({ duck: e.currentTarget.checked })}
      />
      {t('editor.audio.duck')}
    </label>
  </section>
</div>
