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
    /** The chosen host, or null for automatic. */
    avatar: string | null;
    cta_text: string | null;
  };
</script>

<script lang="ts">
  import { loadPreferences } from '$lib/stores/preferences';
  import { onMount, untrack } from 'svelte';
  import { t, tn } from '$lib/i18n/index.svelte';
  import { api } from '$lib/api';
  import AvatarImage from '$lib/components/avatars/AvatarImage.svelte';
  import AvatarPicker from '$lib/components/avatars/AvatarPicker.svelte';
  import { effectiveHost, hostInfo, hostPrefs, loadHosts } from '$lib/components/avatars/hosts.svelte';
  import Modal from '$lib/components/ui/Modal.svelte';
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
    initial = {},
    onsubmit
  }: {
    busy?: boolean;
    error?: unknown;
    /** Pre-selected kind of video and prompt, e.g. from the Home page. */
    initial?: { purpose?: string; prompt?: string; aspect?: string; duration?: number };
    onsubmit: (value: CreateValue) => void;
  } = $props();

  let purposes = $state<PurposeTemplate[]>([]);
  // Only the starting values matter; later changes to `initial` must not reset the form.
  const start = untrack(() => initial);
  const preferences = loadPreferences();
  let purposeKey = $state(start.purpose ?? preferences.purpose);
  let prompt = $state(start.prompt ?? '');
  let duration = $state(60);
  let language = $state<string>(preferences.language);
  let style = $state('storytelling');
  let aspect = $state('9:16');
  let tone = $state('');
  let audience = $state('');
  let presenter = $state(true);
  let ctaText = $state('');
  // null is "automatic": the favourite adapted to the video type, or the type's own host.
  let avatar = $state<string | null>(null);
  let choosingHost = $state(false);
  const resolvedHost = $derived(avatar ?? effectiveHost(purposeKey, hostPrefs()));
  const hostName = $derived(hostInfo(resolvedHost)?.name ?? '');
  // An example is only a placeholder until the user types; switching purpose
  // swaps it again, but never overwrites text the user wrote.
  let promptTouched = !!start.prompt;

  const current = $derived(purposes.find((p) => p.key === purposeKey) ?? null);
  /** A word from the dictionary, or the server's own text when there is no entry for it. */
  const word = (key: string, fallback: string) => {
    const s = t(key);
    return s === key ? fallback : s;
  };
  const labelOf = (p: PurposeTemplate) => word(`purpose.${p.key}.label`, p.label);
  const descOf = (p: PurposeTemplate) => word(`purpose.${p.key}.description`, p.description);
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
  const aspectOptions = $derived([
    { value: '9:16', label: '9:16', hint: t('ai.aspect.vertical') },
    { value: '16:9', label: '16:9', hint: t('ai.aspect.landscape') },
    { value: '1:1', label: '1:1', hint: t('ai.aspect.square') }
  ]);
  const languageOptions = [
    { value: 'en', label: 'English' },
    { value: 'km', label: 'ខ្មែរ' }
  ];

  const prettyDuration = $derived(
    duration < 60 ? t('ai.durationSeconds', { n: duration }) : tn('ai.durationMinute', duration / 60)
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
    void loadHosts();
    try {
      purposes = await api.purposes();
      const first = purposes.find((p) => p.key === purposeKey) ?? purposes[0];
      if (first) choose(first);
      // A template's own shape and length win over the purpose's defaults.
      if (start.aspect) aspect = start.aspect;
      if (start.duration) duration = start.duration;
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
      avatar: presenter ? avatar : null,
      cta_text: ctaText.trim() || null
    });
  }

  const step =
    'grid h-6 w-6 shrink-0 place-items-center rounded-full bg-sun-500/15 text-xs font-bold text-sun-300';
</script>

<form class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_21rem] lg:items-start" onsubmit={submit}>
  <div class="flex min-w-0 flex-col gap-9">
    <header>
      <h1 class="text-[30px] leading-tight font-bold tracking-tight text-slate-50">
        {t('ai.title')}
      </h1>
      <p class="mt-1.5 max-w-xl text-sm leading-relaxed text-slate-400">
        {t('ai.intro')}
      </p>
    </header>

    <!-- 1 · purpose -->
    <section class="flex flex-col gap-3.5">
      <h2 class="flex items-center gap-2.5 text-base font-semibold text-slate-100">
        <span class={step}>1</span> {t('ai.step1')}
      </h2>
      <div class="grid grid-cols-2 gap-3 xl:grid-cols-3" role="radiogroup" aria-label={t('ai.purpose')}>
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
            <span class="text-sm font-semibold text-slate-50">{labelOf(template)}</span>
            <span class="text-xs leading-relaxed text-slate-400">{descOf(template)}</span>
          </button>
        {/each}
      </div>
    </section>

    <!-- 2 · describe -->
    <section class="flex flex-col gap-3.5">
      <h2 class="flex items-center gap-2.5 text-base font-semibold text-slate-100">
        <span class={step}>2</span>
        {current?.key === 'product_demo' ? t('ai.step2Product') : t('ai.step2')}
      </h2>
      <div class="flex flex-col gap-2">
        <textarea
          bind:value={prompt}
          oninput={() => (promptTouched = true)}
          rows="4"
          required
          maxlength="2000"
          aria-label={t('ai.prompt')}
          class="w-full resize-y px-3.5 py-3 text-[15px] leading-relaxed"
          placeholder={current?.example_prompt ?? t('ai.promptPlaceholder')}
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
              <Icon name="sparkles" size={13} /> {t('ai.useExample')}
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
        <span class={step}>3</span> {t('ai.step3')}
      </h2>
      <div class="grid gap-4 sm:grid-cols-2">
        <Field label={t('ai.language')}>
          <Segmented options={languageOptions} bind:value={language} label={t('ai.language')} />
        </Field>
        <Field label={t('ai.shape')}>
          <Segmented options={aspectOptions} bind:value={aspect} label={t('ai.aspectRatio')} />
        </Field>
      </div>
      <Field label={t('ai.length')}>
        <Segmented options={durationOptions} bind:value={duration} label={t('ai.duration')} />
      </Field>

      <details class="group surface">
        <summary
          class="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 text-sm font-medium text-slate-200 select-none"
        >
          {t('ai.moreOptions')}
          <Icon
            name="chevronDown"
            size={16}
            class="text-slate-400 transition group-open:rotate-180"
          />
        </summary>
        <div class="grid gap-4 border-t border-slate-800 p-4 sm:grid-cols-2">
          <Field label={t('ai.style')}>
            <select bind:value={style} class="h-10 w-full px-3 text-sm">
              {#each styles as value (value)}
                <option {value}>{word(`ai.style.${value}`, value.replace('_', ' '))}</option>
              {/each}
            </select>
          </Field>
          <Field label={t('ai.cta')} hint={t('ai.ctaHint')}>
            <input
              bind:value={ctaText}
              class="h-10 w-full px-3 text-sm"
              maxlength="60"
              placeholder={t('ai.ctaPlaceholder')}
            />
          </Field>
          <Field label={t('ai.tone')}>
            <input bind:value={tone} class="h-10 w-full px-3 text-sm" maxlength="64" />
          </Field>
          <Field label={t('ai.audience')}>
            <input bind:value={audience} class="h-10 w-full px-3 text-sm" maxlength="128" />
          </Field>
          <label class="flex items-center gap-2.5 text-sm text-slate-300 sm:col-span-2">
            <input type="checkbox" bind:checked={presenter} />
            {t('ai.showHost')}
          </label>
        </div>
      </details>

      {#if presenter}
        <div class="surface flex items-center gap-3.5 p-3">
          <AvatarImage src={hostInfo(resolvedHost)?.image} name={hostName || '?'} fit={hostInfo(resolvedHost)?.custom ? 'cover' : 'contain'} class="h-16 w-14 shrink-0 rounded-xl bg-slate-950" />
          <div class="min-w-0 flex-1">
            <p class="text-xs font-medium text-slate-400">{t('ai.host')}</p>
            <p class="truncate text-sm font-semibold text-slate-50">
              {hostName}
              {#if avatar === null}<span class="ml-1 text-xs font-normal text-slate-500">· {t('avatars.automatic')}</span>{/if}
            </p>
            <p class="text-xs text-slate-500">{avatar === null ? t('avatars.create.hint') : t('avatars.title')}</p>
          </div>
          <Button variant="secondary" size="sm" onclick={() => (choosingHost = true)}>{t('avatars.create.change')}</Button>
        </div>
      {/if}
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
            <Icon name="user" size={10} /> {t('ai.host')}
          </span>
        {/if}
      </div>
    </div>

    <dl class="flex flex-col gap-2.5 text-sm">
      {#each [[t('ai.purpose'), current ? labelOf(current) : t('ai.story')], [t('ai.length'), prettyDuration], [t('ai.shape'), `${aspect} · ${portrait ? t('ai.shapeVertical') : ratio[0] === ratio[1] ? t('ai.shapeSquare') : t('ai.shapeLandscape')}`], [t('ai.language'), language === 'km' ? t('ai.langKhmer') : t('ai.langEnglish')], [t('ai.host'), presenter ? hostName || t('ai.hostAnimated') : t('ai.hostVoiceOnly')]] as [label, value] (label)}
        <div class="flex items-baseline justify-between gap-4">
          <dt class="text-slate-400">{label}</dt>
          <dd class="text-right font-medium text-slate-100">{value}</dd>
        </div>
      {/each}
    </dl>

    <div class="hidden lg:block"><ErrorBanner {error} /></div>

    <div class="flex flex-col gap-2.5">
      <Button type="submit" loading={busy} icon="sparkles" class="h-11 w-full">
        {t('ai.generate')}
      </Button>
      <p class="text-center text-xs leading-relaxed text-slate-500">
        {t('ai.generateNote')}
      </p>
    </div>
  </aside>
</form>

{#if choosingHost}
  <Modal wide title={t('avatars.create.chooseTitle')} onclose={() => (choosingHost = false)}>
    <div class="max-h-[68vh] overflow-y-auto pr-1">
    <AvatarPicker
      allowAuto
      value={avatar}
      onselect={(id) => {
        avatar = id;
        choosingHost = false;
      }}
    />
    </div>
  </Modal>
{/if}
