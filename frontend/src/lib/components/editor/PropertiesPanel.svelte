<script lang="ts">
  import CaptionEditor from '$lib/components/editor/CaptionEditor.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Field from '$lib/components/ui/Field.svelte';
  import type { Scene } from '$lib/types/api';

  let {
    scene,
    busy = false,
    onsave,
    ondelete,
    onduplicate,
    onregenerateVoice
  }: {
    scene: Scene | null;
    busy?: boolean;
    onsave: (id: string, patch: Partial<Scene>) => void;
    ondelete: (id: string) => void;
    onduplicate: (id: string) => void;
    onregenerateVoice: (id: string) => void;
  } = $props();

  // Local draft so typing does not fire a request per keystroke.
  let narration = $state('');
  let onScreenText = $state('');
  let duration = $state(5);
  let transition = $state('fade');
  let background = $state('#0b0d12');
  let loadedId = $state<string | null>(null);

  $effect(() => {
    if (scene && scene.id !== loadedId) {
      loadedId = scene.id;
      narration = scene.narration;
      onScreenText = scene.on_screen_text ?? '';
      duration = scene.duration;
      transition = scene.transition;
      background = scene.background_color;
    }
  });

  const input = 'w-full rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm';

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

</script>

<aside class="flex w-full flex-col gap-4 lg:w-80">
  {#if !scene}
    <p class="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-500">
      Select a scene to edit it.
    </p>
  {:else}
    <h3 class="text-xs font-semibold tracking-wide text-slate-400 uppercase">
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
        <input type="number" min="1" max="120" step="0.1" bind:value={duration} class={input} />
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
      <Button onclick={save} loading={busy}>Save</Button>
      <Button variant="secondary" onclick={() => onregenerateVoice(scene.id)} loading={busy}>
        Regenerate voice
      </Button>
    </div>

    {#if scene.audio_url}
      <div class="flex flex-col gap-1">
        <span class="text-xs font-medium tracking-wide text-slate-400 uppercase">Voice</span>
        <!-- svelte-ignore a11y_media_has_caption -->
        <audio controls src={scene.audio_url} class="w-full"></audio>
      </div>
    {/if}

    <div class="flex flex-col gap-1">
      <span class="text-xs font-medium tracking-wide text-slate-400 uppercase">Captions</span>
      <CaptionEditor captions={scene.captions} />
    </div>

    <div class="mt-2 flex gap-2 border-t border-slate-800 pt-3">
      <Button variant="secondary" onclick={() => onduplicate(scene.id)}>Duplicate</Button>
      <Button variant="danger" onclick={() => ondelete(scene.id)}>Delete scene</Button>
    </div>
  {/if}
</aside>
