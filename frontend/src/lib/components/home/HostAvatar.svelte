<script lang="ts">
  /**
   * The Home banner's animated host: the same cartoon presenter that hosts every exported
   * video, talking, blinking and gesturing in a loop, with a speech bubble that follows
   * the beat and little chips floating around it. Loaded only on wide screens.
   */
  import { fly, fade } from 'svelte/transition';
  import Icon, { type IconName } from '$lib/components/ui/Icon.svelte';
  import { customHosts, effectiveHost, hostPrefs, loadHosts } from '$lib/components/avatars/hosts.svelte';
  import { t } from '$lib/i18n/index.svelte';

  const LINES = ['home.host.1', 'home.host.2', 'home.host.3', 'home.host.4', 'home.host.5', 'home.host.6'];
  const CHIPS: { key: string; icon: IconName; style: string; delay: string }[] = [
    { key: 'home.chip.script', icon: 'book', style: 'left:0.25rem; top:36%', delay: '0s' },
    { key: 'home.chip.voice', icon: 'mic', style: 'right:0.25rem; top:48%', delay: '1.1s' },
    { key: 'home.chip.captions', icon: 'captions', style: 'left:0.5rem; top:68%', delay: '2.2s' }
  ];

  let host = $state<HTMLElement | undefined>();
  let line = $state(0);

  $effect(() => {
    if (!host) return;
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    let controller: { destroy: () => void } | undefined;
    let timer: ReturnType<typeof setInterval> | undefined;
    let cancelled = false;
    // React and Remotion load only when this component is actually on screen.
    // The banner shows YOUR host: the favourite (or the default for a story), or an uploaded photo.
    void Promise.all([import('$lib/remotion/host'), loadHosts().catch(() => {})]).then(([m]) => {
      if (cancelled || !host) return;
      const id = effectiveHost('story', hostPrefs());
      const custom = customHosts().find((c) => c.id === id);
      controller = m.mountHost(
        host,
        !reduce,
        custom
          ? { kind: 'photo', id, imageUrl: custom.image_url, mode: custom.mode }
          : { kind: 'builtin', id, imageUrl: null, mode: 'mouth' }
      );
      if (!reduce) timer = setInterval(() => (line = (line + 1) % LINES.length), m.BEAT_MS);
    });
    return () => {
      cancelled = true;
      controller?.destroy();
      if (timer) clearInterval(timer);
    };
  });
</script>

<div class="pointer-events-none relative mx-auto h-[24rem] w-[19rem] select-none" aria-hidden="true">
  <!-- a soft sun glow behind the host, pulsing like a heartbeat -->
  <span class="absolute top-1/3 left-1/2 h-44 w-44 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[image:var(--sun-gradient)] opacity-30 blur-2xl"></span>
  <span class="animate-ring-ping absolute top-1/3 left-1/2 h-40 w-40 -translate-x-1/2 -translate-y-1/2 rounded-full border border-sun-400/40"></span>

  <div bind:this={host} class="absolute inset-0 animate-pop-in"></div>

  <!-- the speech bubble: a new line every beat -->
  <div class="absolute -top-2 left-1/2 w-60 -translate-x-1/2">
    {#key line}
      <p
        class="rounded-2xl rounded-bl-sm border border-white/15 bg-slate-950/80 px-4 py-2.5 text-center text-sm font-medium text-slate-100 shadow-xl shadow-black/40 backdrop-blur"
        in:fly={{ y: 10, duration: 420 }}
        out:fade={{ duration: 160 }}
      >
        {t(LINES[line])}
      </p>
    {/key}
  </div>

  {#each CHIPS as chip (chip.key)}
    <span
      class="animate-bob absolute inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-slate-950/80 px-3 py-1.5 text-xs font-semibold text-slate-100 shadow-lg shadow-black/40 backdrop-blur"
      style="{chip.style}; animation-delay:{chip.delay}"
    >
      <Icon name={chip.icon} size={13} class="text-sun-300" />{t(chip.key)}
    </span>
  {/each}
</div>
