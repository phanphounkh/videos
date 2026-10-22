<script lang="ts" module>
  export type CreateValue = {
    prompt: string;
    duration: number;
    language: string;
    style: string;
    aspect_ratio: string;
    tone: string;
    audience: string;
    purpose: string;
    presenter: boolean;
    cta_text: string | null;
  };
</script>

<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Field from '$lib/components/ui/Field.svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import Segmented from '$lib/components/ui/Segmented.svelte';
  import type { PurposeTemplate } from '$lib/types/api';

  /** The "what video do you want to create?" form, with a live summary beside it. */
  let {
    busy = false,
    error = null,
    onsubmit
  }: {
    busy?: boolean;
    error?: unknown;
    onsubmit: (value: CreateValue) => void;
  } = $props();

  let purposes = $state<PurposeTemplate[]>([]);
  let purposeKey = $state('story');
  let prompt = $state('');
  let duration = $state(60);
  let language = $state('en');
  let style = $state('storytelling');
  let aspect = $state('9:16');
  let tone = $state('');
  let audience = $state('');
  let presenter = $state(true);
  let ctaText = $state('');
  // An example is only a placeholder until the user types; switching purpose
  // swaps it again, but never overwrites text the user wrote.
  let promptTouched = false;

  const current = $derived(purposes.find((p) => p.key === purposeKey) ?? null);
  const styles = [
    'social_media',
    'storytelling',
    'cinematic',
    'educational',
    'documentary',
    'minimal',
    'technology'
  ];

  const icons: Record<string, IconName> = {
    story: 'book',
    product_demo: 'package',
    social_post: 'phone',
    creator: 'video',
    explainer: 'lightbulb'
  };
  const iconOf = (key: string): IconName => icons[key] ?? 'film';

  const durationOptions = [
    { value: 15, label: '15s' },
    { value: 30, label: '30s' },
    { value: 60, label: '1m' },
    { value: 90, label: '1.5m' },
    { value: 180, label: '3m' },
    { value: 300, label: '5m' }
  ];
  const aspectOptions = [
    { value: '9:16', label: '9:16', hint: 'Vertical: Reels, TikTok, Shorts' },
    { value: '16:9', label: '16:9', hint: 'Landscape: YouTube, websites' },
    { value: '1:1', label: '1:1', hint: 'Square: feeds' }
  ];
  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'km', label: 'ខ្មែរ' }
  ];

  const prettyDuration = $derived(
    duration < 60 ? `${duration} seconds` : `${duration / 60} minute${duration === 60 ? '' : 's'}`
  );
  const ratio = $derived(aspect.split(':').map(Number) as [number, number]);
  const portrait = $derived(ratio[1] > ratio[0]);

  function choose(template: PurposeTemplate) {
    purposeKey = template.key;
    duration = template.duration;
    style = template.style;
    aspect = template.aspect_ratio;
    tone = template.tone;
    audience = template.audience;
    presenter = template.presenter;
    ctaText = template.cta_text ?? '';
    if (!promptTouched) prompt = template.example_prompt;
  }

  onMount(async () => {
    try {
      purposes = await api.purposes();
      const first = purposes.find((p) => p.key === purposeKey) ?? purposes[0];
      if (first) choose(first);
    } catch {
      // The form still works without templates: it creates a plain story.
    }
  });

  function submit(event: SubmitEvent) {
    event.preventDefault();
    onsubmit({
      prompt,
      duration,
      language,
      style,
      aspect_ratio: aspect,
      tone,
      audience,
      purpose: purposeKey,
      presenter,
      cta_text: ctaText.trim() || null
    });
  }

  const step =
    'grid h-6 w-6 shrink-0 place-items-center rounded-full bg-sun-500/15 text-xs font-bold text-sun-300';
</script>

<form class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_21rem] lg:items-start" onsubmit={submit}>
  <div class="flex min-w-0 flex-col gap-9">
    <header>
      <h1 class="text-[28px] leading-tight font-semibold tracking-tight text-slate-50">
        Create a video
      </h1>
      <p class="mt-1.5 max-w-xl text-sm leading-relaxed text-slate-400">
        Pick what it is for, describe it, and Sorya writes the script, scenes, voice and captions.
        You can edit everything afterwards.
      </p>
    </header>

    <!-- 1 · purpose -->
    <section class="flex flex-col gap-3.5">
      <h2 class="flex items-center gap-2.5 text-base font-semibold text-slate-100">
        <span class={step}>1</span> What is it for?
      </h2>
      <div class="grid grid-cols-2 gap-3 xl:grid-cols-3" role="radiogroup" aria-label="Purpose">
        {#if !purposes.length}
          {#each [0, 1, 2] as n (n)}
            <div class="h-28 animate-pulse rounded-xl border border-slate-800 bg-slate-900"></div>
          {/each}
        {/if}
        {#each purposes as template (template.key)}
          {@const selected = template.key === purposeKey}
          <button
            type="button"
            role="radio"
            aria-checked={selected}
            onclick={() => choose(template)}
            class="group flex flex-col gap-2 rounded-xl border p-3.5 text-left transition sm:p-4 {selected
              ? 'border-sun-400/70 bg-sun-500/10 shadow-glow'
              : 'border-slate-800 bg-slate-900 hover:border-slate-600 hover:bg-slate-800/60'}"
          >
            <span
              class="grid h-9 w-9 place-items-center rounded-lg transition {selected
                ? 'bg-[image:var(--sun-gradient)] text-sun-950'
                : 'bg-slate-800 text-slate-300 group-hover:text-slate-100'}"
            >
              <Icon name={iconOf(template.key)} size={18} />
            </span>
            <span class="text-sm font-semibold text-slate-50">{template.label}</span>
            <span class="text-xs leading-relaxed text-slate-400">{template.description}</span>
          </button>
        {/each}
      </div>
    </section>

    <!-- 2 · describe -->
    <section class="flex flex-col gap-3.5">
      <h2 class="flex items-center gap-2.5 text-base font-semibold text-slate-100">
        <span class={step}>2</span>
        {current?.key === 'product_demo' ? 'Describe your product' : 'Describe your video'}
      </h2>
      <div class="flex flex-col gap-2">
        <textarea
          bind:value={prompt}
          oninput={() => (promptTouched = true)}
          rows="4"
          required
          maxlength="2000"
          aria-label="Prompt"
          class="w-full resize-y px-3.5 py-3 text-[15px] leading-relaxed"
          placeholder={current?.example_prompt ?? 'What is the video about?'}
        ></textarea>
        <div class="flex items-center justify-between gap-3 text-xs text-slate-500">
          {#if current}
            <button
              type="button"
              class="inline-flex items-center gap-1.5 rounded-md text-slate-400 transition hover:text-sun-300"
              onclick={() => {
                prompt = current.example_prompt;
                promptTouched = false;
              }}
            >
              <Icon name="sparkles" size={13} /> Use an example
            </button>
          {:else}
            <span></span>
          {/if}
          <span class="tabular-nums">{prompt.length} / 2000</span>
        </div>
      </div>
    </section>

    <!-- 3 · format -->
    <section class="flex flex-col gap-4">
      <h2 class="flex items-center gap-2.5 text-base font-semibold text-slate-100">
        <span class={step}>3</span> Format
      </h2>
      <div class="grid gap-4 sm:grid-cols-2">
        <Field label="Language">
          <Segmented options={languageOptions} bind:value={language} label="Language" />
        </Field>
        <Field label="Shape">
          <Segmented options={aspectOptions} bind:value={aspect} label="Aspect ratio" />
        </Field>
      </div>
      <Field label="Length">
        <Segmented options={durationOptions} bind:value={duration} label="Duration" />
      </Field>

      <details class="group surface">
        <summary
          class="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-slate-200 select-none"
        >
          More options
          <Icon
            name="chevronDown"
            size={16}
            class="text-slate-400 transition group-open:rotate-180"
          />
        </summary>
        <div class="grid gap-4 border-t border-slate-800 p-4 sm:grid-cols-2">
          <Field label="Style">
            <select bind:value={style} class="h-10 w-full px-3 text-sm">
              {#each styles as value (value)}
                <option {value}>{value.replace('_', ' ')}</option>
              {/each}
            </select>
          </Field>
          <Field label="Closing button" hint="Shown at the end, e.g. “Shop now”. Empty keeps “Follow”.">
            <input
              bind:value={ctaText}
              class="h-10 w-full px-3 text-sm"
              maxlength="60"
              placeholder="Follow"
            />
          </Field>
          <Field label="Tone">
            <input bind:value={tone} class="h-10 w-full px-3 text-sm" maxlength="64" />
          </Field>
          <Field label="Audience">
            <input bind:value={audience} class="h-10 w-full px-3 text-sm" maxlength="128" />
          </Field>
          <label class="flex items-center gap-2.5 text-sm text-slate-300 sm:col-span-2">
            <input type="checkbox" bind:checked={presenter} />
            Show the animated host on screen
          </label>
        </div>
      </details>
    </section>

    <div class="lg:hidden"><ErrorBanner {error} /></div>
  </div>

  <!-- live summary -->
  <aside class="surface flex flex-col gap-5 p-5 lg:sticky lg:top-6">
    <div class="flex h-52 items-center justify-center rounded-xl bg-slate-950 p-4">
      <div
        class="relative flex items-center justify-center overflow-hidden rounded-lg border border-slate-700 bg-gradient-to-br from-slate-800 via-slate-900 to-sun-950/60 shadow-pop transition-all duration-300"
        style="aspect-ratio:{ratio[0]}/{ratio[1]}; {portrait
          ? 'height:100%'
          : 'width:100%'}; max-width:100%; max-height:100%"
      >
        <div
          class="pointer-events-none absolute -top-8 left-1/2 h-24 w-24 -translate-x-1/2 rounded-full bg-sun-500/30 blur-2xl"
        ></div>
        <span class="relative grid h-11 w-11 place-items-center rounded-xl bg-slate-950/60 text-sun-300 backdrop-blur">
          <Icon name={iconOf(purposeKey)} size={22} />
        </span>
        {#if presenter}
          <span
            class="absolute bottom-2 left-2 inline-flex items-center gap-1 rounded-full bg-slate-950/70 px-2 py-0.5 text-[10px] text-slate-300"
          >
            <Icon name="user" size={10} /> Host
          </span>
        {/if}
      </div>
    </div>

    <dl class="flex flex-col gap-2.5 text-sm">
      {#each [['Purpose', current?.label ?? 'Story'], ['Length', prettyDuration], ['Shape', `${aspect} · ${portrait ? 'vertical' : ratio[0] === ratio[1] ? 'square' : 'landscape'}`], ['Language', language === 'km' ? 'ខ្មែរ (Khmer)' : 'English'], ['Host', presenter ? 'Animated host' : 'Voice-over only']] as [label, value] (label)}
        <div class="flex items-baseline justify-between gap-4">
          <dt class="text-slate-400">{label}</dt>
          <dd class="text-right font-medium text-slate-100">{value}</dd>
        </div>
      {/each}
    </dl>

    <div class="hidden lg:block"><ErrorBanner {error} /></div>

    <div class="flex flex-col gap-2.5">
      <Button type="submit" loading={busy} icon="sparkles" class="h-11 w-full">
        Generate video
      </Button>
      <p class="text-center text-xs leading-relaxed text-slate-500">
        Narration is generated in the background once the script is ready.
      </p>
    </div>
  </aside>
</form>
