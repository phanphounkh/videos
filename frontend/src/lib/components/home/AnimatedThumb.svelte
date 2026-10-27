<script lang="ts">
  /**
   * A template's cover picture that comes alive while `active` (the card is hovered or
   * focused): the picture stays underneath and the live drawing fades in over it, so
   * there is never a blank frame. React and Remotion load on the first hover only.
   */
  import type { TemplateItem } from '$lib/types/api';

  let {
    template,
    active = false,
    fit = 'cover',
    class: extra = ''
  }: { template: TemplateItem; active?: boolean; fit?: 'cover' | 'contain'; class?: string } = $props();

  let host = $state<HTMLElement | undefined>();
  let ready = $state(false);

  $effect(() => {
    if (!active || !host || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let controller: { destroy: () => void } | undefined;
    let cancelled = false;
    let fade: ReturnType<typeof setTimeout> | undefined;
    void import('$lib/remotion/thumb').then((m) => {
      if (cancelled || !host) return;
      controller = m.mountThumb(host, template);
      // Give the first frame a moment to paint before revealing it.
      fade = setTimeout(() => (ready = true), 120);
    });
    return () => {
      cancelled = true;
      clearTimeout(fade);
      ready = false;
      controller?.destroy();
    };
  });
</script>

<span class="relative block h-full w-full overflow-hidden {extra}">
  <img src={template.thumbnail_url} alt="" loading="lazy" class="h-full w-full {fit === 'cover' ? 'object-cover' : 'object-contain'}" />
  {#if active}
    <span bind:this={host} class="pointer-events-none absolute inset-0 block transition-opacity duration-200 {ready ? 'opacity-100' : 'opacity-0'}" aria-hidden="true"></span>
  {/if}
</span>
