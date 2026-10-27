<script lang="ts">
  /**
   * Where "Generate" lands: shows the AI working (script, narration, finishing),
   * then plays the finished video. "Edit" opens the full editor.
   */
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { api } from '$lib/api';
  import VideoPreview from '$lib/components/editor/VideoPreview.svelte';
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import Icon from '$lib/components/ui/Icon.svelte';
  import { t } from '$lib/i18n/index.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import type { Project, Scene } from '$lib/types/api';

  const projectId = $derived(page.params.id as string);

  let project = $state<Project | null>(null);
  let scenes = $state<Scene[]>([]);
  let error = $state<unknown>(null);
  let attempts = $state(0);
  let time = $state(0);
  let playing = $state(false);
  const MAX_POLLS = 120; // ~5 minutes at 2.5s

  async function load() {
    try {
      const detail = await api.getProjectDetail(projectId);
      project = detail.project;
      scenes = detail.scenes;
      error = null;
    } catch (e) {
      error = e;
    }
  }

  $effect(() => {
    if (!auth.ready) return;
    if (!auth.user) void goto('/login', { replaceState: true });
    else if (!project) void load();
  });

  const narrated = $derived(scenes.filter((s) => s.narration.trim() !== ''));
  const voiced = $derived(narrated.filter((s) => s.audio_url).length);
  const failed = $derived(project?.status === 'failed');
  const scriptDone = $derived(scenes.length > 0);
  const voiceDone = $derived(scriptDone && voiced === narrated.length);
  const finished = $derived(
    !!project && !failed && project.status !== 'generating' && voiceDone
  );
  const timedOut = $derived(attempts >= MAX_POLLS);

  // Rough overall progress: script 30%, narration 60%, finishing 10%.
  const percent = $derived(
    finished
      ? 100
      : Math.round(
          (scriptDone ? 30 : 0) +
            (narrated.length ? (voiced / narrated.length) * 60 : 0) +
            (voiceDone && project?.status !== 'generating' ? 10 : 0)
        )
  );

  const steps = $derived([
    { key: 'script', done: scriptDone, detail: scriptDone ? t('progress.scenes', { n: scenes.length }) : '' },
    {
      key: 'voice',
      done: voiceDone,
      detail: narrated.length ? `${voiced} / ${narrated.length}` : ''
    },
    { key: 'finish', done: finished, detail: '' }
  ]);
  const active = $derived(steps.findIndex((s) => !s.done));

  $effect(() => {
    if (!project || finished || failed || timedOut) return;
    const timer = setTimeout(() => {
      attempts += 1;
      void load();
    }, 2500);
    return () => clearTimeout(timer);
  });
</script>

<svelte:head><title>{t('progress.title')} · Sorya</title></svelte:head>

<main class="mx-auto max-w-5xl px-4 py-8 sm:px-6">
  <ErrorBanner {error} />

  {#if project}
    <h1 class="text-2xl font-semibold text-slate-50">{project.title}</h1>

    {#if failed}
      <div class="mt-6 rounded-xl border border-red-500/30 bg-red-500/10 p-5 text-red-200">
        <p class="font-medium">{t('progress.failed')}</p>
        {#if project.error_message}<p class="mt-1 text-sm">{project.error_message}</p>{/if}
        <div class="mt-4 flex gap-2">
          <Button variant="secondary" onclick={() => goto('/create/ai')}>{t('progress.tryAgain')}</Button>
          <Button variant="ghost" onclick={() => goto(`/projects/${projectId}`)}>{t('progress.edit')}</Button>
        </div>
      </div>
    {:else if finished}
      <p class="mt-1 text-sm text-slate-400">{t('progress.done')}</p>
      <div class="mt-6 grid gap-6 lg:grid-cols-[1fr_18rem]">
        <div class="h-[70vh] min-h-96 overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
          <VideoPreview
            {scenes}
            projectTitle={project.title}
            aspectRatio={project.aspect_ratio}
            language={project.language}
            purpose={project.purpose}
            presenter={project.presenter}
            avatar={project.avatar_resolved}
            ctaText={project.cta_text}
            music={project.music}
            musicUrl={project.music_url}
            fps={project.fps}
            width={project.width}
            height={project.height}
            bind:time
            bind:playing
            onlayercommit={() => {}}
            onlayeredit={() => {}}
          />
        </div>
        <div class="flex flex-col gap-3">
          <Button icon="film" onclick={() => goto(`/projects/${projectId}`)}>{t('progress.edit')}</Button>
          <Button variant="secondary" onclick={() => goto('/projects')}>{t('progress.toProjects')}</Button>
        </div>
      </div>
    {:else}
      <p class="mt-1 text-sm text-slate-400">{t('progress.working')}</p>
      <div class="mt-6 rounded-xl border border-slate-800 bg-slate-900/60 p-6">
        <div class="h-2 overflow-hidden rounded-full bg-slate-800">
          <div class="h-full bg-[image:var(--sun-gradient)] transition-all duration-500" style="width:{percent}%"></div>
        </div>
        <p class="mt-2 text-right text-xs text-slate-400 tabular-nums">{percent}%</p>
        <ol class="mt-4 space-y-4">
          {#each steps as step, i (step.key)}
            <li class="flex items-center gap-3">
              <span
                class="grid h-7 w-7 place-items-center rounded-full text-xs {step.done
                  ? 'bg-emerald-500/20 text-emerald-300'
                  : i === active
                    ? 'bg-sun-500/20 text-sun-300'
                    : 'bg-slate-800 text-slate-500'}"
              >
                {#if step.done}<Icon name="check" size={14} />{:else}
                  <span class={i === active ? 'animate-pulse' : ''}>{i + 1}</span>
                {/if}
              </span>
              <span class={step.done || i === active ? 'text-slate-100' : 'text-slate-500'}>
                {t(`progress.step.${step.key}`)}
              </span>
              {#if step.detail}<span class="text-sm text-slate-400">{step.detail}</span>{/if}
            </li>
          {/each}
        </ol>
        {#if timedOut}
          <p class="mt-5 text-sm text-slate-400">{t('progress.slow')}</p>
          <Button class="mt-3" variant="secondary" onclick={() => goto(`/projects/${projectId}`)}>{t('progress.edit')}</Button>
        {/if}
      </div>
    {/if}
  {/if}
</main>
