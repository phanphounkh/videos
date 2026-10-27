<script lang="ts">
  /** Right-hand panel: the selected text/sticker's properties, else the selected scene's. */
  import LayerPanel from '$lib/components/editor/LayerPanel.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import Field from '$lib/components/ui/Field.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import Segmented from '$lib/components/ui/Segmented.svelte';
  import { layersOf, round } from '$lib/editor/layers';
  import { t, tn } from '$lib/i18n/index.svelte';
  import type { Layer, Scene } from '$lib/types/api';

  let {
    scene,
    selectedLayerId = $bindable<string | null>(null),
    textfocus = 0,
    busy = false,
    onsave,
    ondelete,
    onduplicate,
    onregenerateVoice,
    onsettings,
    onlayers,
    onopencaptions,
    onupload,
    onclearmedia
  }: {
    scene: Scene | null;
    selectedLayerId?: string | null;
    textfocus?: number;
    busy?: boolean;
    onsave: (id: string, patch: Partial<Scene>) => void;
    ondelete: (id: string) => void;
    onduplicate: (id: string) => void;
    onregenerateVoice: (id: string) => void;
    onsettings: (sceneId: string, patch: Record<string, unknown>) => void;
    onlayers: (sceneId: string, layers: Layer[]) => void;
    /** Jump to the Captions panel to edit this scene's captions. */
    onopencaptions: () => void;
    onupload: (file: File, sceneId: string) => void;
    onclearmedia: (sceneId: string) => void;
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

  let layerTab = $state<'design' | 'animate'>('design');
  // A newly chosen text or sticker starts on Design.
  let lastLayer: string | null = null;
  $effect(() => {
    if (selectedLayerId !== lastLayer) layerTab = 'design';
    lastLayer = selectedLayerId;
  });
  const title = $derived(
    layer ? (layer.type === 'sticker' ? t('editor.props.sticker') : t('editor.props.text')) : scene ? t('editor.props.scene', { n: scene.scene_number }) : t('editor.props.title')
  );
</script>

<aside
  class="flex max-h-[30rem] w-full shrink-0 flex-col border-t border-slate-800 bg-slate-900/40 lg:max-h-none lg:w-[19rem] lg:border-t-0 lg:border-l"
>
  <div class="flex h-12 shrink-0 items-center justify-between border-b border-slate-800 px-4">
    <h2 class="text-sm font-semibold text-slate-50">{title}</h2>
    <span class="text-xs text-slate-500">{t('editor.props.title')}</span>
  </div>

  <div class="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto p-4">
  {#if !scene}
    <p class="rounded-lg border border-dashed border-slate-800 p-4 text-sm text-slate-500">
      {t('editor.props.selectScene')}
    </p>
  {:else if layer}
    <Segmented
      label={t('editor.props.textProps')}
      options={[
        { value: 'design', label: t('editor.props.design') },
        { value: 'animate', label: t('editor.props.animate') }
      ]}
      bind:value={layerTab}
    />
    <LayerPanel
      {scene}
      {layer}
      {textfocus}
      mode={layerTab}
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
    <Field label={t('editor.props.narration')} hint={t('editor.props.narrationHint')}>
      <textarea
        bind:value={narration}
        rows="4"
        class="{input} resize-y"
        class:km={(scene.language ?? 'en').startsWith('km')}
      ></textarea>
    </Field>

    <Field label={t('editor.props.point')} hint={t('editor.props.pointHint')}>
      <input bind:value={onScreenText} class={input} maxlength="500" />
    </Field>

    <div class="grid grid-cols-2 gap-3">
      <Field label={t('editor.props.duration')}>
        <input type="number" min="0.5" max="120" step="0.1" bind:value={duration} class={input} />
      </Field>
      <Field label={t('editor.props.transition')}>
        <select bind:value={transition} class={input}>
          <option value="fade">{t('editor.transition.fade')}</option>
          <option value="slide">{t('editor.transition.slide')}</option>
          <option value="none">{t('editor.transition.none')}</option>
        </select>
      </Field>
    </div>

    <Field label={t('editor.props.background')}>
      <input type="color" bind:value={background} class="h-9 w-full rounded bg-slate-950" />
    </Field>

    <div class="flex flex-wrap gap-2">
      <Button onclick={save} loading={busy} icon="check">{t('editor.props.save')}</Button>
      <Button variant="secondary" icon="mic" onclick={() => onregenerateVoice(scene.id)} loading={busy}>
        {t('editor.props.regen')}
      </Button>
    </div>

    <!-- picture or clip -->
    <section class="flex flex-col gap-3 border-t border-slate-800 pt-4">
      <h3 class="section-title">{t('editor.props.media')}</h3>
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
            <div class="flex h-full items-center justify-center text-[10px] text-slate-600">{t('editor.props.none')}</div>
          {/if}
        </div>
        <div class="flex flex-col gap-1.5">
          <Button variant="secondary" size="sm" icon="upload" onclick={() => fileInput?.click()}>{t('editor.props.upload')}</Button>
          {#if scene.image_url || scene.video_url}
            <Button variant="ghost" size="sm" icon="trash" onclick={() => onclearmedia(scene.id)}>{t('editor.props.remove')}</Button>
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
        <Field label={t('editor.props.fit')}>
          <select
            value={fit}
            onchange={(e) => onsettings(scene.id, { media_fit: e.currentTarget.value === 'cover' ? null : e.currentTarget.value })}
            class={input}
          >
            <option value="cover">{t('editor.props.fill')}</option>
            <option value="contain">{t('editor.props.contain')}</option>
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
          {t('editor.props.slowZoom')}
        </label>
      {/if}

      {#if scene.video_url}
        <Field
          label={t('editor.props.clipStart')}
          hint={scene.video_duration
            ? t('editor.props.clipLength', { n: scene.video_duration.toFixed(1) })
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
              {t('editor.props.fitClip', { n: remaining.toFixed(1) })}
            </Button>
          {/if}
          {#if scene.duration > remaining + 0.1}
            <p class="text-xs text-amber-300">
              {t('editor.props.longer')}
            </p>
          {/if}
        {/if}
      {/if}
    </section>

    {#if scene.audio_url}
      <div class="flex flex-col gap-1">
        <span class="section-title">{t('editor.props.voice')}</span>
        <!-- svelte-ignore a11y_media_has_caption -->
        <audio controls src={scene.audio_url} class="w-full"></audio>
      </div>
    {/if}

    <button
      class="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/50 px-3.5 py-3 text-left transition hover:border-slate-600"
      onclick={onopencaptions}
    >
      <span class="flex flex-col">
        <span class="text-sm font-medium text-slate-100">{t('editor.tool.captions')}</span>
        <span class="text-xs text-slate-500">
          {tn('editor.props.captionCount', scene.captions.length)}{scene.settings?.captions_edited ? t('editor.props.byHand') : ''}
        </span>
      </span>
      <span class="flex items-center gap-1 text-xs font-medium text-sun-300">{t('editor.props.edit')} <Icon name="captions" size={14} /></span>
    </button>

    <div class="mt-2 flex gap-2 border-t border-slate-800 pt-3">
      <Button variant="secondary" size="sm" icon="copy" onclick={() => onduplicate(scene.id)}>{t('common.duplicate')}</Button>
      <Button variant="danger" size="sm" icon="trash" onclick={() => ondelete(scene.id)}>{t('editor.props.deleteScene')}</Button>
    </div>
  {/if}
  </div>
</aside>
