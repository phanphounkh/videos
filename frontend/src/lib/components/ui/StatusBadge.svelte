<script lang="ts">
  import type { ProjectStatus, RenderStatus } from '$lib/types/api';

  let { status }: { status: ProjectStatus | RenderStatus | string } = $props();

  const tone: Record<string, string> = {
    draft: 'bg-slate-700/60 text-slate-200',
    generating: 'bg-amber-500/20 text-amber-300',
    ready: 'bg-emerald-500/20 text-emerald-300',
    rendering: 'bg-indigo-500/20 text-indigo-300',
    uploading: 'bg-indigo-500/20 text-indigo-300',
    preparing: 'bg-indigo-500/20 text-indigo-300',
    queued: 'bg-slate-600/50 text-slate-200',
    completed: 'bg-emerald-500/20 text-emerald-300',
    failed: 'bg-red-500/20 text-red-300'
  };
</script>

<span
  class="rounded-full px-2 py-0.5 text-xs font-medium capitalize {tone[status] ??
    'bg-slate-700/60 text-slate-200'}"
>
  {status.replace('_', ' ')}
</span>
