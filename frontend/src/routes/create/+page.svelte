<script lang="ts">
  /**
   * Create a video, step by step: set up the canvas, bring in media, open the editor.
   * Starting from a template or from a prompt (Generate with AI) are the other ways in.
   */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import { bytes, mmss } from '$lib/format';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import { t, tn } from '$lib/i18n/index.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { loadPreferences } from '$lib/stores/preferences';
  import { track } from '$lib/telemetry/client';
  import type { Folder } from '$lib/types/api';

  type Picked = { id: string; file: File; url: string; kind: 'image' | 'video' | 'audio'; seconds: number | null };

  const ASPECTS: { value: string; label: string; name: string; icon: IconName; w: number; h: number }[] = [
    { value: '16:9', label: '16:9', name: 'create.aspect.landscape', icon: 'monitor', w: 16, h: 9 },
    { value: '9:16', label: '9:16', name: 'create.aspect.portrait', icon: 'phone', w: 9, h: 16 },
    { value: '1:1', label: '1:1', name: 'create.aspect.square', icon: 'square', w: 1, h: 1 }
  ];
  const BASE: Record<string, [number, number]> = { '16:9': [1920, 1080], '9:16': [1080, 1920], '1:1': [1080, 1080] };

  let name = $state('Untitled video');
  let start = $state<'blank' | 'import'>('blank');
  let aspect = $state(page.url.searchParams.get('aspect') ?? '16:9');
  let resolution = $state<'fhd' | 'hd'>('fhd');
  let fps = $state(30);
  let folderId = $state(page.url.searchParams.get('folder') ?? '');
  let folders = $state<Folder[]>([]);
  let picked = $state<Picked[]>([]);
  let dragging = $state(false);
  let busy = $state('');
  let error = $state<unknown>(null);
  let fileInput = $state<HTMLInputElement>();

  $effect(() => {
    if (auth.ready && !auth.user) void goto('/login', { replaceState: true });
    else if (auth.user) api.listFolders().then((f) => (folders = f)).catch(() => {});
  });
  // The Home page's "Import media" tile arrives with ?import=1.
  $effect(() => {
    if (page.url.searchParams.get('import') === '1') start = 'import';
  });

  const dims = $derived.by(() => {
    const [w, h] = BASE[aspect] ?? BASE['16:9'];
    return resolution === 'hd' ? [Math.round((w * 2) / 3 / 2) * 2, Math.round((h * 2) / 3 / 2) * 2] : [w, h];
  });
  const shape = $derived(ASPECTS.find((a) => a.value === aspect) ?? ASPECTS[0]);
  const firstVisual = $derived(picked.find((p) => p.kind !== 'audio'));
  const step = $derived(busy ? 3 : picked.length ? 2 : 1);

  function add(files: FileList | File[]) {
    for (const file of files) {
      const kind = file.type.startsWith('image/') ? 'image' : file.type.startsWith('video/') ? 'video' : file.type.startsWith('audio/') ? 'audio' : null;
      if (!kind) continue;
      const item: Picked = { id: crypto.randomUUID(), file, url: URL.createObjectURL(file), kind, seconds: null };
      picked = [...picked, item];
      if (kind !== 'image') {
        const el = document.createElement(kind === 'video' ? 'video' : 'audio');
        el.preload = 'metadata';
        el.onloadedmetadata = () => {
          picked = picked.map((p) => (p.id === item.id ? { ...p, seconds: Number.isFinite(el.duration) ? el.duration : null } : p));
        };
        el.src = item.url;
      }
    }
  }
  function remove(id: string) {
    const gone = picked.find((p) => p.id === id);
    if (gone) URL.revokeObjectURL(gone.url);
    picked = picked.filter((p) => p.id !== id);
  }

  async function create() {
    error = null;
    try {
      busy = t('create.busy.creating');
      const prefs = loadPreferences();
      const project = await api.createProject({
        title: name.trim() || 'Untitled video',
        language: prefs.language,
        aspect_ratio: aspect as never,
        // A blank canvas: the person's own media, no animated host, no AI script.
        purpose: 'creator' as never,
        presenter: false,
        fps,
        resolution,
        folder_id: folderId || null
      });
      let n = 0;
      for (const item of picked) {
        n += 1;
        busy = t('create.busy.adding', { n, total: picked.length });
        if (item.kind === 'audio') {
          await api.uploadMusic(project.id, item.file);
          continue;
        }
        const scene = await api.createScene(project.id, {
          narration: '',
          duration: item.kind === 'video' ? Math.min(Math.max(item.seconds ?? 5, 1), 60) : 4
        } as never);
        await api.uploadMedia(project.id, item.file, scene.id);
      }
      track('create.blank', { aspect, resolution, fps, media: picked.length });
      await goto(`/projects/${project.id}`);
    } catch (e) {
      error = e;
      busy = '';
    }
  }

  const field = 'h-11 w-full rounded-xl border border-slate-700 bg-slate-950 px-3.5 text-sm text-slate-100 focus:border-sun-400 focus:outline-none';
  const card = (on: boolean) =>
    `flex items-start gap-3 rounded-xl border p-3.5 text-left transition ${on ? 'border-sun-400 bg-sun-400/10' : 'border-slate-700 bg-slate-900/40 hover:border-slate-500'}`;
</script>

<svelte:head><title>{t('create.pageTitle')} · Sorya</title></svelte:head>

<main class="mx-auto max-w-[120rem] px-4 py-6 sm:px-6 lg:px-10">
  <nav class="text-sm text-slate-400" aria-label={t('create.breadcrumb')}>
    <a href="/projects" class="hover:text-slate-100">{t('projects.title')}</a>
    <span class="mx-1.5 text-slate-600">/</span>
    <span class="text-slate-200">{t('create.newProject')}</span>
  </nav>
  <h1 class="mt-2 text-[30px] leading-tight font-bold tracking-tight text-slate-50">{t('create.heading')}</h1>
  <p class="mt-1 text-slate-400">{t('create.subtitle')}</p>

  <ol class="mt-6 flex items-center gap-3 text-sm" aria-label={t('create.steps')}>
    {#each ['setup', 'media', 'editor'] as label, i (label)}
      {@const n = i + 1}
      <li class="flex items-center gap-3 {n < 3 ? 'flex-1' : ''}">
        <span class="grid h-8 w-8 shrink-0 place-items-center rounded-full text-sm font-bold {step >= n ? 'bg-[image:var(--sun-gradient)] text-sun-950' : 'bg-slate-800 text-slate-400'}" aria-current={step === n ? 'step' : undefined}>
          {#if step > n}<Icon name="check" size={15} />{:else}{n}{/if}
        </span>
        <span class="font-medium {step >= n ? 'text-slate-100' : 'text-slate-500'}">{t(`create.step.${label}`)}</span>
        {#if n < 3}<span class="h-px flex-1 bg-slate-700"></span>{/if}
      </li>
    {/each}
  </ol>

  <div class="mt-6">
    <ErrorBanner {error} />
  </div>

  <div class="mt-2 grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]">
    <!-- setup -->
    <section class="flex flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/40 p-5 sm:p-6">
      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-200">
        {t('create.projectName')}
        <input class={field} bind:value={name} maxlength="300" data-private />
      </label>

      <div>
        <p class="mb-2 text-sm font-semibold text-slate-200">{t('create.startWith')}</p>
        <div class="grid grid-cols-2 gap-3">
          <button type="button" class={card(start === 'blank')} aria-pressed={start === 'blank'} onclick={() => (start = 'blank')}>
            <Icon name="film" size={22} class="mt-0.5 text-sun-300" />
            <span><span class="block text-sm font-semibold text-slate-50">{t('create.blank')}</span><span class="text-xs text-slate-400">{t('create.blankHint')}</span></span>
          </button>
          <button type="button" class={card(start === 'import')} aria-pressed={start === 'import'} onclick={() => ((start = 'import'), fileInput?.click())}>
            <Icon name="upload" size={22} class="mt-0.5 text-sun-300" />
            <span><span class="block text-sm font-semibold text-slate-50">{t('create.import')}</span><span class="text-xs text-slate-400">{t('create.importHint')}</span></span>
          </button>
          <a href="/templates" class={card(false)}>
            <Icon name="templates" size={22} class="mt-0.5 text-sun-300" />
            <span><span class="block text-sm font-semibold text-slate-50">{t('create.template')}</span><span class="text-xs text-slate-400">{t('create.templateHint')}</span></span>
          </a>
          <a href="/create/ai" class={card(false)}>
            <Icon name="sparkles" size={22} class="mt-0.5 text-sun-300" />
            <span><span class="block text-sm font-semibold text-slate-50">{t('create.ai')}</span><span class="text-xs text-slate-400">{t('create.aiHint')}</span></span>
          </a>
        </div>
      </div>

      <div>
        <p class="mb-2 text-sm font-semibold text-slate-200">{t('create.aspect')}</p>
        <div class="grid grid-cols-3 gap-3" role="radiogroup" aria-label={t('create.aspect')}>
          {#each ASPECTS as a (a.value)}
            <button type="button" role="radio" aria-checked={aspect === a.value} class="flex flex-col items-center gap-2 rounded-xl border px-3 py-4 transition {aspect === a.value ? 'border-sun-400 bg-sun-400/10' : 'border-slate-700 bg-slate-900/40 hover:border-slate-500'}" onclick={() => (aspect = a.value)}>
              <span class="grid h-10 w-14 place-items-center">
                <span class="rounded-md border-2 {aspect === a.value ? 'border-sun-300' : 'border-slate-400'}" style="width:{(a.w / Math.max(a.w, a.h)) * 40}px; height:{(a.h / Math.max(a.w, a.h)) * 40}px"></span>
              </span>
              <span class="text-sm font-semibold {aspect === a.value ? 'text-sun-200' : 'text-slate-100'}">{t(a.name)}</span>
              <span class="text-xs text-slate-400">{a.label}</span>
            </button>
          {/each}
        </div>
      </div>

      <div class="grid gap-4 sm:grid-cols-2">
        <label class="flex flex-col gap-2 text-sm font-semibold text-slate-200">
          {t('create.resolution')}
          <select class={field} bind:value={resolution}>
            <option value="fhd">{BASE[aspect][0]} × {BASE[aspect][1]} ({t('create.fullHd')})</option>
            <option value="hd">{Math.round((BASE[aspect][0] * 2) / 3 / 2) * 2} × {Math.round((BASE[aspect][1] * 2) / 3 / 2) * 2} ({t('create.hd')})</option>
          </select>
        </label>
        <label class="flex flex-col gap-2 text-sm font-semibold text-slate-200">
          {t('create.frameRate')}
          <select class={field} bind:value={fps}>
            <option value={24}>24 fps</option>
            <option value={30}>30 fps</option>
            <option value={60}>60 fps</option>
          </select>
        </label>
      </div>

      <label class="flex flex-col gap-2 text-sm font-semibold text-slate-200">
        {t('create.folder')}
        <select class={field} bind:value={folderId}>
          <option value="">{t('create.noFolder')}</option>
          {#each folders as f (f.id)}<option value={f.id}>{f.name}</option>{/each}
        </select>
      </label>
    </section>

    <!-- preview + media -->
    <section class="flex flex-col gap-4">
      <div class="overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
        <div class="flex items-center justify-between px-4 py-2.5 text-xs text-slate-400"><span class="font-medium text-slate-200">{t('create.preview')}</span><span>{aspect}</span></div>
        <div class="grid h-64 place-items-center px-4 pb-2">
          <div class="relative max-h-full max-w-full overflow-hidden rounded-lg border-2 border-sun-400/70 bg-gradient-to-br from-slate-800 to-slate-900" style="aspect-ratio:{shape.w}/{shape.h}; height:{shape.h > shape.w ? '100%' : 'auto'}; width:{shape.h > shape.w ? 'auto' : shape.w === shape.h ? '16rem' : '100%'}; max-height:15rem">
            {#if firstVisual?.kind === 'image'}
              <img src={firstVisual.url} alt="" class="h-full w-full object-cover" />
            {:else if firstVisual?.kind === 'video'}
              <!-- svelte-ignore a11y_media_has_caption -->
              <video src={firstVisual.url} muted class="h-full w-full object-cover"></video>
            {:else}
              <div class="grid h-full w-full place-items-center text-slate-500"><Icon name="film" size={30} /></div>
            {/if}
          </div>
        </div>
        <p class="pb-3 text-center text-xs text-slate-500">{dims[0]} × {dims[1]}</p>
      </div>

      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="flex flex-col items-center gap-2 rounded-2xl border-2 border-dashed px-5 py-6 text-center transition {dragging || start === 'import' ? 'border-sun-400 bg-sun-400/5' : 'border-slate-700'}"
        ondragover={(e) => (e.preventDefault(), (dragging = true))}
        ondragleave={() => (dragging = false)}
        ondrop={(e) => {
          e.preventDefault();
          dragging = false;
          if (e.dataTransfer?.files) add(e.dataTransfer.files);
        }}
      >
        <Icon name="upload" size={26} class="text-slate-400" />
        <p class="text-sm font-semibold text-slate-100">{t('create.drop')}</p>
        <p class="text-xs text-slate-500">{t('create.or')}</p>
        <Button size="sm" onclick={() => fileInput?.click()}>{t('create.browse')}</Button>
        <p class="text-xs text-slate-500">{t('create.supports')}</p>
        <input bind:this={fileInput} type="file" multiple accept="image/*,video/*,audio/*" class="hidden" onchange={(e) => (add(e.currentTarget.files ?? []), (e.currentTarget.value = ''))} />
      </div>

      {#if picked.length}
        <ul class="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {#each picked as item (item.id)}
            <li class="group relative overflow-hidden rounded-xl border border-slate-800 bg-slate-900/60">
              <div class="grid aspect-video place-items-center bg-slate-950 text-slate-500">
                {#if item.kind === 'image'}<img src={item.url} alt="" class="h-full w-full object-cover" />
                {:else if item.kind === 'video'}
                  <!-- svelte-ignore a11y_media_has_caption -->
                  <video src={item.url} muted preload="metadata" class="h-full w-full object-cover"></video>
                {:else}<Icon name="music" size={24} />{/if}
              </div>
              {#if item.seconds}<span class="absolute right-1.5 bottom-[3.2rem] rounded bg-slate-950/80 px-1.5 py-0.5 font-mono text-[11px] text-slate-100">{mmss(item.seconds)}</span>{/if}
              <button type="button" class="absolute top-1.5 right-1.5 grid h-6 w-6 place-items-center rounded-full bg-slate-950/80 text-slate-200 hover:bg-red-500/80" aria-label={t('create.remove', { name: item.file.name })} onclick={() => remove(item.id)}><Icon name="x" size={13} /></button>
              <div class="px-2.5 py-2"><p class="truncate text-xs font-medium text-slate-100" data-private>{item.file.name}</p><p class="text-[11px] text-slate-500">{bytes(item.file.size)}</p></div>
            </li>
          {/each}
        </ul>
      {/if}
    </section>
  </div>
</main>

<div class="sticky bottom-0 z-30 border-t border-slate-800 bg-slate-950/95 px-4 py-3 backdrop-blur">
  <div class="mx-auto flex max-w-6xl items-center justify-between gap-3">
    <a href="/projects"><Button variant="secondary">{t('create.cancel')}</Button></a>
    <div class="flex items-center gap-2">
      {#if busy}<span class="mr-1 flex items-center gap-2 text-sm text-slate-300"><span class="h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-transparent"></span>{busy}</span>{/if}
      <a href="/templates"><Button variant="secondary" disabled={!!busy}>{t('create.useTemplate')}</Button></a>
      <Button onclick={create} disabled={!!busy || !name.trim()}>{t('create.createProject')}</Button>
    </div>
  </div>
</div>
