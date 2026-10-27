<script lang="ts" module>
  export type MenuItem = {
    label: string;
    icon?: import('$lib/components/ui/Icon.svelte').IconName;
    onclick: () => void;
    danger?: boolean;
    /** A thin line is drawn above this item. */
    separator?: boolean;
  };
</script>

<script lang="ts">
  /** A small dropdown opened by a button: the "⋯" menu on cards and folders. */
  import Icon from '$lib/components/ui/Icon.svelte';

  let {
    items,
    label = 'More actions',
    align = 'right',
    class: extra = ''
  }: { items: MenuItem[]; label?: string; align?: 'left' | 'right'; class?: string } = $props();

  let open = $state(false);
  let root = $state<HTMLElement | undefined>();
  let button = $state<HTMLButtonElement | undefined>();
  let panel = $state<HTMLElement | undefined>();
  // Where the open menu sits, in window coordinates. It is drawn on <body> (see `portal`),
  // so no card, clipping box or stacking order can ever hide it.
  let place = $state({ top: 0, left: 0, up: false });

  const WIDTH = 208; // w-52

  function position() {
    if (!button) return;
    const r = button.getBoundingClientRect();
    const height = panel?.offsetHeight ?? items.length * 40 + 8;
    const up = r.bottom + 8 + height > window.innerHeight && r.top - 8 - height > 0;
    const left = align === 'right' ? r.right - WIDTH : r.left;
    place = {
      top: up ? r.top - 4 - height : r.bottom + 4,
      left: Math.min(Math.max(8, left), window.innerWidth - WIDTH - 8),
      up
    };
  }

  /** Moves the element to <body> while it exists. */
  function portal(node: HTMLElement) {
    document.body.appendChild(node);
    position();
    return { destroy: () => node.remove() };
  }

  $effect(() => {
    if (!open) return;
    const away = (e: PointerEvent) => {
      const target = e.target as Node;
      if (root?.contains(target) || panel?.contains(target)) return;
      open = false;
    };
    // The menu is placed in window coordinates, so it closes if anything moves under it.
    const close = () => (open = false);
    window.addEventListener('scroll', close, true);
    window.addEventListener('resize', close);
    const key = (e: KeyboardEvent) => e.key === 'Escape' && (open = false);
    document.addEventListener('pointerdown', away);
    document.addEventListener('keydown', key);
    return () => {
      document.removeEventListener('pointerdown', away);
      document.removeEventListener('keydown', key);
      window.removeEventListener('scroll', close, true);
      window.removeEventListener('resize', close);
    };
  });
</script>

<!-- A caller that positions the menu itself (absolute) must not be forced back to relative. -->
<div class="{extra.includes('absolute') ? '' : 'relative'} {extra}" bind:this={root}>
  <button
    bind:this={button}
    type="button"
    class="grid h-8 w-8 place-items-center rounded-lg bg-slate-950/70 text-slate-200 backdrop-blur transition hover:bg-slate-800"
    aria-haspopup="menu"
    aria-expanded={open}
    aria-label={label}
    onclick={(e) => {
      e.preventDefault();
      e.stopPropagation();
      open = !open;
    }}><Icon name="more" size={16} /></button
  >
  {#if open}
    <div
      use:portal
      bind:this={panel}
      role="menu"
      class="fixed z-[100] w-52 overflow-hidden rounded-xl border border-slate-700 bg-slate-900 py-1 shadow-2xl shadow-black/50"
      style="top:{place.top}px; left:{place.left}px"
    >
      {#each items as item (item.label)}
        {#if item.separator}<div class="my-1 border-t border-slate-800"></div>{/if}
        <button
          type="button"
          role="menuitem"
          class="flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition hover:bg-slate-800 {item.danger
            ? 'text-red-300'
            : 'text-slate-200'}"
          onclick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            open = false;
            item.onclick();
          }}
        >
          {#if item.icon}<Icon name={item.icon} size={15} />{/if}
          {item.label}
        </button>
      {/each}
    </div>
  {/if}
</div>
