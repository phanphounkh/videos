<script lang="ts">
  import { t } from '$lib/i18n/index.svelte';
  import type { ProjectStatus, RenderStatus } from '$lib/types/api';

  let { status }: { status: ProjectStatus | RenderStatus | string } = $props();

  // dot colour + text colour; working states pulse.
  const tone: Record<string, [string, string]> = {
    draft: ['bg-slate-500', 'text-slate-300'],
    generating: ['bg-sun-400', 'text-sun-200'],
    ready: ['bg-emerald-400', 'text-emerald-300'],
    rendering: ['bg-sun-400', 'text-sun-200'],
    uploading: ['bg-sun-400', 'text-sun-200'],
    preparing: ['bg-sun-400', 'text-sun-200'],
    queued: ['bg-slate-400', 'text-slate-300'],
    completed: ['bg-emerald-400', 'text-emerald-300'],
    failed: ['bg-red-400', 'text-red-300']
  };
  const working = $derived(['generating', 'rendering', 'uploading', 'preparing'].includes(status));
  const [dot, text] = $derived(tone[status] ?? ['bg-slate-500', 'text-slate-300']);
</script>

<span
  class="inline-flex items-center gap-1.5 rounded-full bg-slate-800/80 px-2.5 py-1 text-xs font-medium capitalize {text}"
>
  <span class="h-1.5 w-1.5 rounded-full {dot} {working ? 'animate-pulse' : ''}"></span>
  {t(`status.${status}`)}
</span>
