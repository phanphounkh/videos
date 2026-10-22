<script lang="ts">
  /**
   * Edit one scene's captions: wording, timing, add, remove, reset.
   *
   * Rows are a local draft that follows the saved captions whenever those really
   * change (undo, a split, new narration). A change is saved when a field is
   * released; a row that is not valid yet (empty, overlapping, out of the scene)
   * is outlined and explained instead of being sent.
   */
  import { untrack } from 'svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import { clamp, round } from '$lib/editor/layers';
  import type { Scene } from '$lib/types/api';

  type Row = { text: string; start: number; end: number };

  let {
    scene,
    at,
    oncommit,
    onreset,
    onseek
  }: {
    scene: Scene;
    /** The playhead inside this scene in seconds, or -1 when it is elsewhere. */
    at: number;
    oncommit: (captions: { text: string; start_time: number; end_time: number }[]) => void;
    onreset: () => void;
    /** Move the playhead to this many seconds into the scene. */
    onseek: (seconds: number) => void;
  } = $props();

  const toRows = (): Row[] =>
    scene.captions.map((c) => ({ text: c.text, start: c.start_time, end: c.end_time }));

  let rows = $state<Row[]>(untrack(toRows));
  let syncedKey = '';
  $effect(() => {
    const key = JSON.stringify([scene.id, scene.duration, scene.captions.map((c) => [c.text, c.start_time, c.end_time])]);
    if (key !== syncedKey) {
      syncedKey = key;
      rows = toRows();
    }
  });

  const edited = $derived(scene.settings?.captions_edited === true);
  const khmer = $derived((scene.language ?? 'en').startsWith('km'));
  const activeIndex = $derived(rows.findIndex((r) => at >= r.start && at < r.end));

  /** What is wrong with the draft, if anything: [row index, message]. */
  const problem = $derived.by((): [number, string] | null => {
    const sorted = rows.map((row, index) => ({ row, index })).sort((a, b) => a.row.start - b.row.start);
    let previousEnd = -Infinity;
    for (const { row, index } of sorted) {
      if (row.text.trim() === '') return [index, 'A caption cannot be empty.'];
      if (!(row.start >= 0)) return [index, 'The start time cannot be negative.'];
      if (row.start >= scene.duration - 0.05) return [index, `It starts after the scene ends (${scene.duration.toFixed(1)}s).`];
      if (!(row.end - row.start >= 0.1)) return [index, 'A caption must last at least 0.1s.'];
      if (row.end > scene.duration + 0.001) return [index, `It ends after the scene ends (${scene.duration.toFixed(1)}s).`];
      if (row.start < previousEnd - 0.01) return [index, 'Captions cannot overlap. End one before the next starts.'];
      previousEnd = row.end;
    }
    return null;
  });

  function save(list: Row[] = rows) {
    if (list === rows && problem) return;
    oncommit(
      [...list]
        .sort((a, b) => a.start - b.start)
        .map((r) => ({ text: r.text.trim(), start_time: round(r.start, 3), end_time: round(r.end, 3) }))
    );
  }

  let hint = $state<string | null>(null);
  let focusRow = $state<number | null>(null);

  /** A new caption at the playhead, in the free space around it. */
  function add() {
    const sorted = [...rows].sort((a, b) => a.start - b.start);
    const want = clamp(at >= 0 ? at : 0, 0, Math.max(0, scene.duration - 0.2));
    const before = [...sorted].reverse().find((r) => r.start <= want);
    const start = round(before && before.end > want ? before.end : want, 2);
    const next = sorted.find((r) => r.start > start - 1e-6 && r.start >= start);
    const end = round(Math.min(start + 1.5, next ? next.start : scene.duration), 2);
    if (end - start < 0.2) {
      hint = 'There is no room at the playhead. Move it to a gap, or shorten a caption first.';
      return;
    }
    hint = null;
    const created: Row = { text: khmer ? 'អត្ថបទថ្មី' : 'New caption', start, end };
    const next_rows = [...rows, created].sort((a, b) => a.start - b.start);
    focusRow = next_rows.indexOf(created);
    rows = next_rows;
    save(next_rows);
  }

  function remove(index: number) {
    const next_rows = rows.filter((_, i) => i !== index);
    rows = next_rows;
    save(next_rows);
  }

  const field = 'w-full px-2 py-1.5 text-sm';
  const time = 'w-[4.5rem] px-2 py-1 font-mono text-xs tabular-nums';
</script>

<div class="flex flex-col gap-3">
  <div class="flex items-center justify-between gap-2">
    <h3 class="section-title flex items-center gap-2">
      Captions · scene {scene.scene_number}
      {#if edited}
        <span class="rounded-full bg-sun-400/15 px-2 py-0.5 text-[10px] font-semibold tracking-normal text-sun-200 normal-case">
          edited
        </span>
      {/if}
    </h3>
  </div>

  <div class="flex flex-wrap gap-2">
    <Button size="sm" icon="plus" onclick={add}>Add caption</Button>
    {#if edited}
      <Button
        size="sm"
        variant="ghost"
        title="Throw away your edits and rebuild captions from the narration"
        onclick={onreset}>Reset to auto</Button
      >
    {/if}
  </div>

  {#if hint}
    <p class="rounded-lg border border-sun-400/30 bg-sun-400/10 px-3 py-2 text-xs text-sun-100">{hint}</p>
  {/if}

  {#if problem}
    <p class="flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-200" role="alert">
      <Icon name="alert" size={14} class="mt-0.5 shrink-0" />
      <span>Caption {problem[0] + 1}: {problem[1]} Nothing is saved until this is fixed.</span>
    </p>
  {/if}

  {#if !rows.length}
    <p class="rounded-xl border border-dashed border-slate-800 p-4 text-center text-sm text-slate-500">
      No captions in this scene.
      {#if edited}Reset to auto to build them from the narration.{:else}Add one at the playhead.{/if}
    </p>
  {/if}

  <ol class="flex flex-col gap-2">
    {#each rows as row, index (index)}
      {@const bad = problem?.[0] === index}
      <li
        class="flex flex-col gap-2 rounded-xl border p-2 transition {bad
          ? 'border-red-500/50 bg-red-500/5'
          : activeIndex === index
            ? 'border-sun-400/60 bg-sun-400/[0.06]'
            : 'border-slate-800 bg-slate-900/50'}"
      >
        <div class="flex items-center gap-1.5">
          <button
            class="grid h-7 w-7 shrink-0 place-items-center rounded-md text-slate-400 transition hover:bg-slate-800 hover:text-slate-100"
            title="Jump the playhead here"
            aria-label="Jump to this caption"
            onclick={() => onseek(row.start + 0.01)}><Icon name="play" size={12} /></button
          >
          <input
            class={time}
            type="number"
            min="0"
            max={scene.duration}
            step="0.1"
            aria-label="Start (seconds)"
            bind:value={row.start}
            onchange={() => save()}
          />
          <span class="text-slate-600">→</span>
          <input
            class={time}
            type="number"
            min="0"
            max={scene.duration}
            step="0.1"
            aria-label="End (seconds)"
            bind:value={row.end}
            onchange={() => save()}
          />
          <span class="flex-1"></span>
          <button
            class="grid h-7 w-7 shrink-0 place-items-center rounded-md text-slate-500 transition hover:bg-red-500/15 hover:text-red-300"
            title="Delete this caption"
            aria-label="Delete caption"
            onclick={() => remove(index)}><Icon name="trash" size={14} /></button
          >
        </div>
        <!-- svelte-ignore a11y_autofocus -->
        <textarea
          class="{field} resize-y"
          class:km={khmer}
          rows="2"
          maxlength="300"
          aria-label="Caption text"
          bind:value={row.text}
          onchange={() => save()}
          autofocus={focusRow === index}
        ></textarea>
      </li>
    {/each}
  </ol>
</div>
