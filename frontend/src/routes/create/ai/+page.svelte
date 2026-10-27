<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import PromptDialog, { type CreateValue } from '$lib/components/projects/PromptDialog.svelte';
  import { page } from '$app/state';
  import { t } from '$lib/i18n/index.svelte';
  import { takeDraft } from '$lib/stores/draft';
  import { auth } from '$lib/stores/auth.svelte';
  import { track } from '$lib/telemetry/client';
  import type { Project } from '$lib/types/api';

  // From the Home page: the chosen kind of video and anything already typed.
  const draft = takeDraft();
  const initial = {
    purpose: page.url.searchParams.get('purpose') ?? draft?.purpose,
    prompt: draft?.prompt,
    aspect: draft?.aspect,
    duration: draft?.duration
  };

  let busy = $state(false);
  let error = $state<unknown>(null);

  $effect(() => {
    if (auth.ready && !auth.user) void goto('/login', { replaceState: true });
  });

  async function create(value: CreateValue) {
    busy = true;
    error = null;
    track('create.started', { purpose: value.purpose, language: value.language });
    try {
      // Two steps on purpose: the project exists (and is visible in the
      // dashboard) even if generation later fails.
      const project = await api.createProject({
        title: value.prompt.slice(0, 80),
        language: value.language,
        aspect_ratio: value.aspect_ratio,
        style: value.style,
        target_duration: value.duration,
        purpose: value.purpose as Project['purpose'],
        presenter: value.presenter,
        avatar: value.avatar,
        cta_text: value.cta_text,
        tone: value.tone,
        audience: value.audience
      });
      const { avatar: _avatar, ...rest } = value; // the host belongs to the project, not the generate call
      // Script writing takes a while, so don't wait for it: the progress page watches
      // the project. Wait briefly so an immediate refusal (e.g. usage limit) still
      // shows here instead of on a page that would wait forever.
      const generating = api.generate(project.id, { ...rest, generate_media: true });
      generating.catch(() => undefined); // after we navigate, failures show as project status
      await Promise.race([generating, new Promise((resolve) => setTimeout(resolve, 1500))]);
      await goto(`/projects/${project.id}/progress`);
    } catch (e) {
      error = e;
      track('create.failed', { purpose: value.purpose });
    } finally {
      busy = false;
    }
  }
</script>

<svelte:head><title>{t('ai.pageTitle')} · Sorya</title></svelte:head>

<main class="mx-auto max-w-[120rem] px-4 py-6 sm:px-6 lg:px-10">
  <PromptDialog {busy} {error} {initial} onsubmit={create} />
</main>
