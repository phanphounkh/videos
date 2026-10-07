<script lang="ts">
  /** Render progress + download. Polls GET /render-jobs/{id} while it runs. */
  import Button from '$lib/components/ui/Button.svelte';
  import ErrorBanner from '$lib/components/ui/ErrorBanner.svelte';
  import StatusBadge from '$lib/components/ui/StatusBadge.svelte';
  import type { RenderJob } from '$lib/types/api';

  let {
    job,
    busy = false,
    error = null,
    onstart,
    onclose
  }: {
    job: RenderJob | null;
    busy?: boolean;
    error?: unknown;
    onstart: () => void;
    onclose: () => void;
  } = $props();

  const running = $derived(
    !!job && !['completed', 'failed'].includes(job.status)
  );
</script>

<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
  <div class="w-full max-w-md rounded-xl border border-slate-800 bg-slate-900 p-6">
    <div class="mb-4 flex items-center justify-between">
      <h2 class="text-lg font-semibold">Export video</h2>
      <button class="text-slate-500 hover:text-slate-300" onclick={onclose}>✕</button>
    </div>

    {#if !job}
      <p class="mb-4 text-sm text-slate-400">
        Rendering runs in a background worker (Remotion + FFmpeg). You can keep editing other
        projects while it works.
      </p>
      <Button onclick={onstart} loading={busy}>Start render</Button>
    {:else}
      <div class="mb-3 flex items-center gap-2">
        <StatusBadge status={job.status} />
        <span class="font-mono text-xs text-slate-400">{job.progress}%</span>
      </div>

      <div class="mb-4 h-2 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          class="h-full rounded-full transition-all {job.status === 'failed'
            ? 'bg-red-500'
            : 'bg-indigo-500'}"
          style={`width:${job.progress}%`}
        ></div>
      </div>

      {#if running}
        <p class="text-sm text-slate-400">
          {job.status === 'queued' ? 'Waiting for a worker…' : 'Working…'}
        </p>
      {/if}

      {#if job.status === 'completed' && job.output_url}
        <div class="flex flex-col gap-3">
          <!-- svelte-ignore a11y_media_has_caption -->
          <video src={job.output_url} controls class="w-full rounded-lg bg-black"></video>
          <a
            href={job.output_url}
            download
            class="inline-flex items-center justify-center rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500"
          >
            Download MP4
          </a>
        </div>
      {/if}

      {#if job.status === 'failed'}
        <p class="rounded-lg border border-red-900/60 bg-red-950/50 p-3 text-sm text-red-200">
          {job.error_message ?? 'The render failed.'}
        </p>
        <div class="mt-3">
          <Button onclick={onstart} loading={busy}>Retry render</Button>
        </div>
      {/if}
    {/if}

    <div class="mt-4">
      <ErrorBanner {error} />
    </div>
  </div>
</div>
