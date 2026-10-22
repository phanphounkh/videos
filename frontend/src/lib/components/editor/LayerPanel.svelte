<script lang="ts">
  /** Edit the selected text or sticker layer. Every control saves when released. */
  import { untrack } from 'svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Field from '$lib/components/ui/Field.svelte';
  import { STICKERS, clamp, newId, round } from '$lib/editor/layers';
  import type { Layer, Scene } from '$lib/types/api';

  let {
    scene,
    layer,
    onchange,
    ondelete,
    onduplicate,
    textfocus = 0
  }: {
    scene: Scene;
    layer: Layer;
    /** Save this layer (the whole layer, already validated). */
    onchange: (layer: Layer) => void;
    ondelete: (layerId: string) => void;
    onduplicate: (copy: Layer) => void;
    /** Changes whenever the canvas asks to start typing (double-click). */
    textfocus?: number;
  } = $props();

  // A local copy so typing does not save on every keystroke. It follows the saved
  // layer whenever that actually changes (undo, drag on the canvas, timeline).
  let form = $state<Layer>(untrack(() => ({ ...layer })));
  let syncedKey = '';
  $effect(() => {
    const key = JSON.stringify(layer);
    if (key !== syncedKey) {
      syncedKey = key;
      form = { ...layer };
    }
  });

  let textInput = $state<HTMLTextAreaElement | HTMLInputElement>();
  let lastFocus = 0;
  $effect(() => {
    if (textfocus !== lastFocus) {
      lastFocus = textfocus;
      textInput?.focus();
      textInput?.select();
    }
  });

  const input = 'w-full px-3 py-2 text-sm';
  const range = 'w-full accent-sun-500';
  const length = $derived(scene.duration);

  /** Save the form, keeping the layer valid: text present, times inside the scene. */
  function commit(patch: Partial<Layer> = {}) {
    const next = { ...form, ...patch };
    next.text = next.text.trim() === '' ? layer.text : next.text;
    next.start = round(clamp(Number(next.start) || 0, 0, Math.max(0, length - 0.2)));
    next.end = round(clamp(Number(next.end) || 0, next.start + 0.2, length));
    next.font_size = clamp(Number(next.font_size) || 6, 1, 60);
    next.rotation = clamp(Number(next.rotation) || 0, -180, 180);
    form = next;
    if (JSON.stringify(next) !== JSON.stringify(layer)) onchange(next);
  }
</script>

<div class="flex flex-col gap-3">
  <h3 class="section-title">
    {form.type === 'sticker' ? 'Sticker' : 'Text'} · scene {scene.scene_number}
  </h3>

  {#if form.type === 'sticker'}
    <div class="grid grid-cols-8 gap-1">
      {#each STICKERS as emoji (emoji)}
        <button
          class="rounded p-1 text-lg hover:bg-slate-800 {form.text === emoji ? 'bg-sun-600/40' : ''}"
          onclick={() => commit({ text: emoji })}>{emoji}</button
        >
      {/each}
    </div>
    <Field label="Emoji">
      <input
        bind:this={textInput}
        bind:value={form.text}
        onchange={() => commit()}
        class={input}
        maxlength="16"
      />
    </Field>
  {:else}
    <Field label="Text">
      <textarea
        bind:this={textInput}
        bind:value={form.text}
        onchange={() => commit()}
        rows="2"
        maxlength="500"
        class="{input} resize-y"
      ></textarea>
    </Field>
  {/if}

  <Field label={`Size · ${form.font_size.toFixed(1)}%`}>
    <input
      type="range"
      min="1"
      max="40"
      step="0.5"
      bind:value={form.font_size}
      onchange={() => commit()}
      class={range}
    />
  </Field>

  <Field label={`Rotation · ${Math.round(form.rotation)}°`}>
    <input
      type="range"
      min="-180"
      max="180"
      step="1"
      bind:value={form.rotation}
      onchange={() => commit()}
      class={range}
    />
  </Field>

  {#if form.type === 'text'}
    <div class="grid grid-cols-2 gap-3">
      <Field label="Colour">
        <input
          type="color"
          bind:value={form.color}
          onchange={() => commit()}
          class="h-9 w-full rounded bg-slate-950"
        />
      </Field>
      <Field label="Weight">
        <select bind:value={form.weight} onchange={() => commit({ weight: Number(form.weight) })} class={input}>
          <option value={500}>regular</option>
          <option value={700}>bold</option>
          <option value={800}>extra bold</option>
          <option value={900}>black</option>
        </select>
      </Field>
    </div>

    <div class="flex items-center gap-3">
      <label class="flex items-center gap-2 text-sm text-slate-300">
        <input
          type="checkbox"
          checked={form.background !== null}
          onchange={(e) => commit({ background: e.currentTarget.checked ? (form.background ?? '#e11d48') : null })}
        />
        Background
      </label>
      {#if form.background !== null}
        <input
          type="color"
          bind:value={form.background}
          onchange={() => commit()}
          class="h-8 w-16 rounded bg-slate-950"
        />
      {/if}
    </div>
  {/if}

  <Field label="Animation">
    <select bind:value={form.animation} onchange={() => commit()} class={input}>
      <option value="pop">pop</option>
      <option value="bounce">bounce</option>
      <option value="fade">fade in</option>
      <option value="slide_up">slide up</option>
      <option value="none">none</option>
    </select>
  </Field>

  <div class="grid grid-cols-2 gap-3">
    <Field label="Appears (s)" hint="From the start of the scene.">
      <input
        type="number"
        min="0"
        max={length}
        step="0.1"
        bind:value={form.start}
        onchange={() => commit()}
        class={input}
      />
    </Field>
    <Field label="Disappears (s)">
      <input
        type="number"
        min="0"
        max={length}
        step="0.1"
        bind:value={form.end}
        onchange={() => commit()}
        class={input}
      />
    </Field>
  </div>

  <div class="flex gap-2 border-t border-slate-800 pt-3">
    <Button
      variant="secondary"
      size="sm"
      icon="copy"
      onclick={() => onduplicate({ ...form, id: newId(), x: Math.min(95, form.x + 5), y: Math.min(95, form.y + 5) })}
    >
      Duplicate
    </Button>
    <Button variant="danger" size="sm" icon="trash" onclick={() => ondelete(layer.id)}>Delete</Button>
  </div>
</div>
