<script lang="ts">
  /** The one button. `primary` is the sun gradient: use it once per screen. */
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';

  type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

  let {
    variant = 'primary',
    size = 'md',
    icon = undefined,
    disabled = false,
    loading = false,
    type = 'button',
    title = undefined,
    class: extra = '',
    onclick = undefined,
    children
  }: {
    variant?: Variant;
    size?: 'sm' | 'md';
    /** Leading icon. */
    icon?: IconName;
    disabled?: boolean;
    loading?: boolean;
    type?: 'button' | 'submit';
    title?: string;
    class?: string;
    onclick?: (event: MouseEvent) => void;
    children?: import('svelte').Snippet;
  } = $props();

  const styles: Record<Variant, string> = {
    primary:
      'bg-[image:var(--sun-gradient)] text-sun-950 shadow-[0_6px_20px_-8px_rgb(255_138_31/0.7)] hover:brightness-110 active:brightness-95',
    secondary:
      'bg-slate-800 text-slate-100 border border-slate-700 hover:bg-slate-700 hover:border-slate-600',
    ghost: 'bg-transparent text-slate-300 hover:bg-slate-800 hover:text-slate-100',
    danger:
      'bg-red-500/10 text-red-300 border border-red-500/30 hover:bg-red-500/20 hover:text-red-200'
  };
  const sizes = { sm: 'h-8 px-2.5 text-xs gap-1.5', md: 'h-9 px-3.5 text-sm gap-2' };
</script>

<button
  {type}
  {title}
  class="inline-flex items-center justify-center rounded-lg font-semibold whitespace-nowrap transition disabled:cursor-not-allowed disabled:opacity-45 {sizes[
    size
  ]} {styles[variant]} {extra}"
  disabled={disabled || loading}
  {onclick}
>
  {#if loading}
    <span class="h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent"
    ></span>
  {:else if icon}
    <Icon name={icon} size={size === 'sm' ? 14 : 16} />
  {/if}
  {@render children?.()}
</button>
