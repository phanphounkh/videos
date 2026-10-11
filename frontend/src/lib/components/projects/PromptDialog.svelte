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

  let prompt = $state('រឿងកំប្លែងខ្លីអំពីយុវជនម្នាក់ដែលយល់ច្រឡំថាឆ្មារបស់គាត់អាចនិយាយបាន។');
  let duration = $state(60);
  let language = $state('km');
  let style = $state('social_media');
  let aspect = $state('9:16');
  let tone = $state('funny, emotional, and fast-paced');
  let audience = $state('Khmer social media viewers');

  const durations = [30, 60, 90, 180, 300];
  const styles = [
    'social_media',
    'storytelling',
    'cinematic',
    'educational',
    'documentary',
    'minimal',
    'technology'
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
    <h2 class="text-xl font-semibold">Create a Khmer entertainment story</h2>
    <p class="text-sm text-slate-400">
      Describe your characters, situation, and desired ending. AI builds one connected story
      with a hook, escalation, twist and payoff, up to 5 minutes long.
    </p>
  </div>

  <Field label="Prompt">
    <textarea
      bind:value={prompt}
      rows="3"
      required
      maxlength="2000"
      class="w-full resize-y rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
      placeholder="Example: A funny ghost story in a Cambodian village with an unexpected ending."
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
      Khmer uses the natural Piseth voice by default. Narration continues in the background.
    </span>
  </div>
</form>
