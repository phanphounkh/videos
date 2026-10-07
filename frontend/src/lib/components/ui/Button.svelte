<script lang="ts">
  /** Small, reusable button. Variants keep styling consistent across pages. */
  type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

  let {
    variant = 'primary',
    disabled = false,
    loading = false,
    type = 'button',
    title = undefined,
    class: extra = '',
    onclick = undefined,
    children
  }: {
    variant?: Variant;
    disabled?: boolean;
    loading?: boolean;
    type?: 'button' | 'submit';
    title?: string;
    class?: string;
    onclick?: (event: MouseEvent) => void;
    children?: import('svelte').Snippet;
  } = $props();

  const styles: Record<Variant, string> = {
    primary: 'bg-indigo-600 text-white hover:bg-indigo-500',
    secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700 border border-slate-700',
    ghost: 'bg-transparent text-slate-300 hover:bg-slate-800',
    danger: 'bg-red-600/90 text-white hover:bg-red-500'
  };
</script>

<button
  {type}
  {title}
  class="inline-flex items-center justify-center gap-2 rounded-lg px-3.5 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50 {styles[
    variant
  ]} {extra}"
  disabled={disabled || loading}
  {onclick}
>
  {#if loading}
    <span
      class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    ></span>
  {/if}
  {@render children?.()}
</button>
