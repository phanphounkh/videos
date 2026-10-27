<script lang="ts">
  /** A host's picture. Until its image exists (or if it fails) a tinted initial stands in. */
  let {
    src,
    name,
    class: extra = '',
    fit = 'contain'
  }: { src: string | null | undefined; name: string; class?: string; fit?: 'contain' | 'cover' } = $props();

  let failed = $state(false);
  $effect(() => {
    src;
    failed = false;
  });
  const initial = $derived(name.trim().charAt(0).toUpperCase() || '?');
</script>

<span class="relative grid place-items-center overflow-hidden bg-gradient-to-br from-slate-700 to-slate-800 {extra}">
  {#if src && !failed}
    <img {src} alt="" loading="lazy" draggable="false" class="h-full w-full {fit === 'cover' ? 'object-cover' : 'object-contain'}" onerror={() => (failed = true)} />
  {:else}
    <span class="select-none text-2xl font-bold text-sun-300/80" aria-hidden="true">{initial}</span>
  {/if}
</span>
