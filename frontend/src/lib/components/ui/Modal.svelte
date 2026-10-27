<script lang="ts">
  /** A centred dialog over a dimmed page. Escape or a click outside closes it. */
  let {
    title,
    onclose,
    children,
    actions = undefined,
    wide = false
  }: {
    title: string;
    onclose: () => void;
    children: import('svelte').Snippet;
    actions?: import('svelte').Snippet;
    /** A big dialog (a video player) instead of the small form-sized one. */
    wide?: boolean;
  } = $props();

  $effect(() => {
    const key = (e: KeyboardEvent) => e.key === 'Escape' && onclose();
    document.addEventListener('keydown', key);
    return () => document.removeEventListener('keydown', key);
  });
</script>

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div
  class="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4 backdrop-blur-sm"
  onclick={(e) => e.target === e.currentTarget && onclose()}
>
  <div
    role="dialog"
    aria-modal="true"
    aria-label={title}
    class="w-full rounded-2xl border border-slate-700 bg-slate-900 p-5 shadow-2xl {wide ? 'max-w-4xl' : 'max-w-md'}"
  >
    <h2 class="text-lg font-semibold text-slate-50">{title}</h2>
    <div class="mt-3 text-sm text-slate-300">{@render children()}</div>
    {#if actions}<div class="mt-5 flex justify-end gap-2">{@render actions()}</div>{/if}
  </div>
</div>
