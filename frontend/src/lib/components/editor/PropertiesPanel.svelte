<script lang="ts">
  /** Right-hand panel: Scene, Text/sticker layer, and Audio tabs. */
  import AudioPanel from '$lib/components/editor/AudioPanel.svelte';
  import CaptionEditor from '$lib/components/editor/CaptionEditor.svelte';
  import LayerPanel from '$lib/components/editor/LayerPanel.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Field from '$lib/components/ui/Field.svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import { layersOf, round } from '$lib/editor/layers';
  import type { Layer, MusicSettings, Project, Scene } from '$lib/types/api';

  export type Tab = 'scene' | 'layer' | 'captions' | 'audio';

  let {
    scene,
    project,
    tab = $bindable<Tab>('scene'),
    selectedLayerId = $bindable<string | null>(null),
    textfocus = 0,
    busy = false,
    onsave,
    ondelete,
    onduplicate,
    onregenerateVoice,
    onsettings,
    onlayers,
    oncaptions,
    onresetcaptions,
    onseek,
    playhead = -1,
    onaddlayer,
    onupload,
    onclearmedia,
    onuploadMusic,
    onremoveMusic,
    onmusic
  }: {
    scene: Scene | null;
    project: Project;
    tab?: Tab;
    selectedLayerId?: string | null;
    textfocus?: number;
    busy?: boolean;
    onsave: (id: string, patch: Partial<Scene>) => void;
    ondelete: (id: string) => void;
    onduplicate: (id: string) => void;
    onregenerateVoice: (id: string) => void;
    onsettings: (sceneId: string, patch: Record<string, unknown>) => void;
    onlayers: (sceneId: string, layers: Layer[]) => void;
    oncaptions: (
      sceneId: string,
      captions: { text: string; start_time: number; end_time: number }[]
    ) => void;
    onresetcaptions: (sceneId: string) => void;
    /** Move the playhead to this many seconds into the selected scene. */
    onseek: (seconds: number) => void;
    /** The playhead inside the selected scene in seconds, or -1. */
    playhead?: number;
    onaddlayer: (kind: 'text' | 'sticker') => void;
    onupload: (file: File, sceneId: string) => void;
    onclearmedia: (sceneId: string) => void;
    onuploadMusic: (file: File) => void;
    onremoveMusic: () => void;
    onmusic: (patch: Partial<MusicSettings>) => void;
  } = $props();

  // Local draft so typing does not fire a request per keystroke. It follows the
  // saved scene whenever that really changes (a trim on the timeline, undo...).
  let narration = $state('');
  let onScreenText = $state('');
  let duration = $state(5);
  let transition = $state('fade');
  let background = $state('#0b0d12');
  let syncedKey = '';
  $effect(() => {
    if (!scene) return;
    const key = JSON.stringify([
      scene.id,
      scene.narration,
      scene.on_screen_text,
      scene.duration,
      scene.transition,
      scene.background_color
    ]);
    if (key !== syncedKey) {
      syncedKey = key;
      narration = scene.narration;
      onScreenText = scene.on_screen_text ?? '';
      duration = scene.duration;
      transition = scene.transition;
      background = scene.background_color;
    }
  });

  const input = 'w-full px-3 py-2 text-sm';
  const layers = $derived(scene ? layersOf(scene) : []);
  const layer = $derived(layers.find((l) => l.id === selectedLayerId) ?? null);

  const fit = $derived((scene?.settings?.media_fit as string | undefined) ?? 'cover');
  const kenBurns = $derived(scene?.settings?.ken_burns !== false);
  const trimStart = $derived(
    typeof scene?.settings?.trim_start === 'number' ? scene.settings.trim_start : 0
  );
  let trimDraft = $state(0);
  $effect(() => void (trimDraft = trimStart));

  let fileInput = $state<HTMLInputElement>();

  function save() {
    if (!scene) return;
    onsave(scene.id, {
      narration,
      on_screen_text: onScreenText || null,
      duration: Number(duration),
      transition,
      background_color: background
    });
  }

  const tabs: { id: Tab; label: string; icon: IconName }[] = [
    { id: 'scene', label: 'Scene', icon: 'film' },
    { id: 'layer', label: 'Text', icon: 'type' },
    { id: 'captions', label: 'Captions', icon: 'captions' },
    { id: 'audio', label: 'Audio', icon: 'volume' }
  ];
</script>

<aside
  class="flex max-h-[30rem] w-full shrink-0 flex-col border-t border-slate-800 bg-slate-900/40 lg:max-h-none lg:w-[21rem] lg:border-t-0 lg:border-l"
>
  <div class="flex shrink-0 gap-1 border-b border-slate-800 p-2" role="tablist">
    {#each tabs as item (item.id)}
      <button
        role="tab"
        aria-selected={tab === item.id}
        class="flex flex-1 items-center justify-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold transition {tab ===
        item.id
          ? 'bg-slate-800 text-slate-50'
          : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'}"
        onclick={() => (tab = item.id)}
      >
        <Icon name={item.icon} size={14} />
        {item.label}
      </button>
    {/each}
  </div>

  <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
  {#if tab === 'audio'}
    <AudioPanel
      {scene}
      {project}
      {busy}
      {onsettings}
      {onuploadMusic}
      {onremoveMusic}
      {onmusic}
    />
  {:else if !scene}
    <p class="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-500">
      Select a scene to edit it.
    </p>
  {:else if tab === 'captions'}
    <CaptionEditor
      {scene}
      at={playhead}
      oncommit={(captions) => oncaptions(scene.id, captions)}
      onreset={() => onresetcaptions(scene.id)}
      {onseek}
    />
  {:else if tab === 'layer'}
    <div class="flex gap-2">
      <Button variant="secondary" size="sm" icon="type" onclick={() => onaddlayer('text')}>Add text</Button>
      <Button variant="secondary" size="sm" icon="smile" onclick={() => onaddlayer('sticker')}>Add sticker</Button>
    </div>
    {#if layer}
      <LayerPanel
        {scene}
        {layer}
        {textfocus}
        onchange={(next) => onlayers(scene.id, layers.map((l) => (l.id === next.id ? next : l)))}
        ondelete={(id) => {
          selectedLayerId = null;
          onlayers(scene.id, layers.filter((l) => l.id !== id));
        }}
        onduplicate={(copy) => {
          selectedLayerId = copy.id;
          onlayers(scene.id, [...layers, copy]);
        }}
      />
    {:else}
      <p class="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-500">
        {layers.length
          ? 'Click a text or sticker on the preview or the timeline to edit it.'
          : 'Add text or a sticker, then drag it on the preview to place it.'}
      </p>
      {#if layers.length}
        <ul class="flex flex-col gap-1">
          {#each layers as item (item.id)}
            <li>
              <button
                class="w-full truncate rounded-lg border border-slate-800 px-3 py-1.5 text-left text-sm hover:border-slate-600"
                onclick={() => (selectedLayerId = item.id)}
              >
                {item.type === 'sticker' ? item.text : `“${item.text}”`}
                <span class="text-xs text-slate-500">
                  {item.start.toFixed(1)}–{item.end.toFixed(1)}s</span
                >
              </button>
            </li>
          {/each}
        </ul>
      {/if}
    {/if}
  {:else}
    <h3 class="section-title">
      Scene {scene.scene_number}
    </h3>

    <Field label="Narration" hint="Spoken text. Drives captions and voice length.">
      <textarea
        bind:value={narration}
        rows="4"
        class="{input} resize-y"
        class:km={(scene.language ?? 'en').startsWith('km')}
      ></textarea>
    </Field>

    <Field label="Important point" hint="Pops up briefly while this scene is spoken.">
      <input bind:value={onScreenText} class={input} maxlength="500" />
    </Field>

    <div class="grid grid-cols-2 gap-3">
      <Field label="Duration (s)">
        <input type="number" min="0.5" max="120" step="0.1" bind:value={duration} class={input} />
      </Field>
      <Field label="Transition">
        <select bind:value={transition} class={input}>
          <option value="fade">fade</option>
          <option value="slide">slide</option>
          <option value="none">none</option>
        </select>
      </Field>
    </div>

    <Field label="Background">
      <input type="color" bind:value={background} class="h-9 w-full rounded bg-slate-950" />
    </Field>

    <div class="flex flex-wrap gap-2">
      <Button onclick={save} loading={busy} icon="check">Save changes</Button>
      <Button variant="secondary" icon="mic" onclick={() => onregenerateVoice(scene.id)} loading={busy}>
        Regenerate voice
      </Button>
    </div>

    <!-- picture or clip -->
    <section class="flex flex-col gap-3 border-t border-slate-800 pt-4">
      <h3 class="section-title">Picture or clip</h3>
      <div class="flex items-center gap-3">
        <div class="h-14 w-24 shrink-0 overflow-hidden rounded bg-slate-950">
          {#if scene.image_url || scene.video_url}
            {#if scene.video_url}
              <!-- svelte-ignore a11y_media_has_caption -->
              <video src={`${scene.video_url}#t=0.1`} preload="metadata" muted class="h-full w-full object-cover"></video>
            {:else}
              <img src={scene.image_url} alt="" class="h-full w-full object-cover" />
            {/if}
          {:else}
            <div class="flex h-full items-center justify-center text-[10px] text-slate-600">none</div>
          {/if}
        </div>
        <div class="flex flex-col gap-1.5">
          <Button variant="secondary" size="sm" icon="upload" onclick={() => fileInput?.click()}>Upload</Button>
          {#if scene.image_url || scene.video_url}
            <Button variant="ghost" size="sm" icon="trash" onclick={() => onclearmedia(scene.id)}>Remove</Button>
          {/if}
        </div>
      </div>
      <input
        bind:this={fileInput}
        type="file"
        accept="image/png,image/jpeg,image/webp,video/mp4,video/webm,.png,.jpg,.jpeg,.webp,.mp4,.webm"
        class="hidden"
        onchange={(e) => {
          const file = e.currentTarget.files?.[0];
          e.currentTarget.value = '';
          if (file) onupload(file, scene.id);
        }}
      />

      {#if scene.image_url || scene.video_url}
        <Field label="Fit">
          <select
            value={fit}
            onchange={(e) => onsettings(scene.id, { media_fit: e.currentTarget.value === 'cover' ? null : e.currentTarget.value })}
            class={input}
          >
            <option value="cover">Fill the frame</option>
            <option value="contain">Show everything</option>
          </select>
        </Field>
      {/if}

      {#if scene.image_url && !scene.video_url}
        <label class="flex items-center gap-2 text-sm text-slate-300">
          <input
            type="checkbox"
            checked={kenBurns}
            onchange={(e) => onsettings(scene.id, { ken_burns: e.currentTarget.checked ? null : false })}
          />
          Slow zoom
        </label>
      {/if}

      {#if scene.video_url}
        <Field
          label="Clip starts at (s)"
          hint={scene.video_duration
            ? `The clip is ${scene.video_duration.toFixed(1)}s long.`
            : undefined}
        >
          <input
            type="number"
            min="0"
            max={scene.video_duration ?? 3600}
            step="0.1"
            bind:value={trimDraft}
            onchange={() => onsettings(scene.id, { trim_start: round(Math.max(0, Number(trimDraft) || 0)) || null })}
            class={input}
          />
        </Field>
        {#if scene.video_duration}
          {@const remaining = Math.max(0.5, scene.video_duration - trimStart)}
          {#if Math.abs(remaining - scene.duration) > 0.1}
            <Button
              variant="secondary"
              onclick={() => onsave(scene.id, { duration: Math.min(120, round(remaining, 1)) })}
            >
              Fit scene to clip ({remaining.toFixed(1)}s)
            </Button>
          {/if}
          {#if scene.duration > remaining + 0.1}
            <p class="text-xs text-amber-300">
              The scene is longer than the rest of the clip, so the clip's last frame will hold.
            </p>
          {/if}
        {/if}
      {/if}
    </section>

    {#if scene.audio_url}
      <div class="flex flex-col gap-1">
        <span class="section-title">Voice</span>
        <!-- svelte-ignore a11y_media_has_caption -->
        <audio controls src={scene.audio_url} class="w-full"></audio>
      </div>
    {/if}

    <button
      class="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/50 px-3.5 py-3 text-left transition hover:border-slate-600"
      onclick={() => (tab = 'captions')}
    >
      <span class="flex flex-col">
        <span class="text-sm font-medium text-slate-100">Captions</span>
        <span class="text-xs text-slate-500">
          {scene.captions.length}
          {scene.captions.length === 1 ? 'caption' : 'captions'}{scene.settings?.captions_edited ? ' · edited by hand' : ''}
        </span>
      </span>
      <span class="flex items-center gap-1 text-xs font-medium text-sun-300">Edit <Icon name="captions" size={14} /></span>
    </button>

    <div class="mt-2 flex gap-2 border-t border-slate-800 pt-3">
      <Button variant="secondary" size="sm" icon="copy" onclick={() => onduplicate(scene.id)}>Duplicate</Button>
      <Button variant="danger" size="sm" icon="trash" onclick={() => ondelete(scene.id)}>Delete scene</Button>
    </div>
  {/if}
  </div>
</aside>
