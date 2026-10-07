<script lang="ts">
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Field from '$lib/components/ui/Field.svelte';

  /** The "what video do you want to create?" form. */
  let {
    busy = false,
    error = null,
    onsubmit
  }: {
    busy?: boolean;
    error?: unknown;
    onsubmit: (value: {
      prompt: string;
      duration: number;
      language: string;
      style: string;
      aspect_ratio: string;
      tone: string;
      audience: string;
    }) => void;
  } = $props();

  let prompt = $state('Create a 60-second beginner-friendly video explaining neural networks.');
  let duration = $state(60);
  let language = $state('en');
  let style = $state('educational');
  let aspect = $state('16:9');
  let tone = $state('clear and friendly');
  let audience = $state('beginners');

  const durations = [30, 60, 90, 180];
  const styles = [
    'educational',
    'cinematic',
    'documentary',
    'social_media',
    'minimal',
    'technology',
    'storytelling'
  ];

  function submit(event: SubmitEvent) {
    event.preventDefault();
    onsubmit({ prompt, duration, language, style, aspect_ratio: aspect, tone, audience });
  }

  const select =
    'rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100';
</script>

<form
  class="flex flex-col gap-5 rounded-xl border border-slate-800 bg-slate-900/60 p-6"
  onsubmit={submit}
>
  <div>
    <h2 class="text-xl font-semibold">What video do you want to create?</h2>
    <p class="text-sm text-slate-400">
      Describe it in one sentence. The script, scenes, visuals, narration and captions are
      generated for you.
    </p>
  </div>

  <Field label="Prompt">
    <textarea
      bind:value={prompt}
      rows="3"
      required
      maxlength="2000"
      class="w-full resize-y rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
      placeholder="Create a 1-minute educational video explaining machine learning for beginners."
    ></textarea>
  </Field>

  <div class="grid gap-4 sm:grid-cols-3">
    <Field label="Language">
      <select bind:value={language} class={select}>
        <option value="en">English</option>
        <option value="km">ខ្មែរ (Khmer)</option>
      </select>
    </Field>

    <Field label="Duration">
      <select bind:value={duration} class={select}>
        {#each durations as value (value)}
          <option {value}>{value < 60 ? `${value} sec` : `${value / 60} min`}</option>
        {/each}
      </select>
    </Field>

    <Field label="Aspect ratio">
      <select bind:value={aspect} class={select}>
        <option value="16:9">16:9 landscape</option>
        <option value="9:16">9:16 vertical</option>
        <option value="1:1">1:1 square</option>
      </select>
    </Field>

    <Field label="Style">
      <select bind:value={style} class={select}>
        {#each styles as value (value)}
          <option {value}>{value.replace('_', ' ')}</option>
        {/each}
      </select>
    </Field>

    <Field label="Tone">
      <input bind:value={tone} class={select} maxlength="64" />
    </Field>

    <Field label="Audience">
      <input bind:value={audience} class={select} maxlength="128" />
    </Field>
  </div>

  <ErrorBanner {error} />

  <div class="flex items-center gap-3">
    <Button type="submit" loading={busy}>Generate video</Button>
    <span class="text-xs text-slate-500">
      Script runs now; images and narration continue in the background.
    </span>
  </div>
</form>
