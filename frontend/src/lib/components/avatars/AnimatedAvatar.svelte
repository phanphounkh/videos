<script lang="ts">
  /**
   * A host that comes alive while `active` (its card is hovered or focused): it talks,
   * blinks and gestures, drawn by the same code that draws it in exported videos. It is
   * laid over the card's still picture and cropped to the head and shoulders; React and
   * Remotion load on the first hover only.
   */
  import { avatarPayload } from './hosts.svelte';

  let { id, active = false }: { id: string; active?: boolean } = $props();

  let host = $state<HTMLElement | undefined>();
  let ready = $state(false);

  $effect(() => {
    if (!active || !host || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    let controller: { destroy: () => void } | undefined;
    let cancelled = false;
    let fade: ReturnType<typeof setTimeout> | undefined;
    void import('$lib/remotion/host').then((m) => {
      if (cancelled || !host) return;
      controller = m.mountHost(host, true, avatarPayload(id));
      fade = setTimeout(() => (ready = true), 140);
    });
    return () => {
      cancelled = true;
      clearTimeout(fade);
      ready = false;
      controller?.destroy();
    };
  });
</script>

{#if active}
  <span class="pointer-events-none absolute inset-0 block overflow-hidden transition-opacity duration-200 {ready ? 'opacity-100' : 'opacity-0'}" aria-hidden="true">
    <!-- the full figure, enlarged so the card shows head and shoulders -->
    <span bind:this={host} class="absolute -top-[2%] -left-[22%] block h-[142%] w-[144%]"></span>
  </span>
{/if}
