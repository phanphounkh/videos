<script lang="ts">
  import { goto } from '$app/navigation';
  import { api } from '$lib/api';
  import PromptDialog, { type CreateValue } from '$lib/components/projects/PromptDialog.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import type { Project } from '$lib/types/api';

  let busy = $state(false);
  let error = $state<unknown>(null);

  $effect(() => {
    if (auth.ready && !auth.user) void goto('/login', { replaceState: true });
  });

  async function create(value: CreateValue) {
    busy = true;
    error = null;
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
        cta_text: value.cta_text,
        tone: value.tone,
        audience: value.audience
      });
      await api.generate(project.id, { ...value, generate_media: true });
      await goto(`/projects/${project.id}`);
    } catch (e) {
      error = e;
    } finally {
      busy = false;
    }
  }
</script>

<main class="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:py-10">
  <PromptDialog {busy} {error} onsubmit={create} />
</main>
