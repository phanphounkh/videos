<script lang="ts">
  /** The Sorya sun mark and wordmark. */
  let { size = 28, wordmark = true }: { size?: number; wordmark?: boolean } = $props();

  // One gradient id per logo on the page: a hidden copy must not take the gradient away.
  const gradient = `sorya-sun-${Math.random().toString(36).slice(2, 8)}`;
</script>

<span class="inline-flex items-center gap-2.5">
  <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
    <defs>
      <linearGradient id={gradient} x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stop-color="#ffc15c" />
        <stop offset="1" stop-color="#ff6a1a" />
      </linearGradient>
    </defs>
    <g stroke="url(#{gradient})" stroke-width="2.4" stroke-linecap="round">
      <path d="M16 2.5v3.2M16 26.3v3.2M2.5 16h3.2M26.3 16h3.2M6.4 6.4l2.3 2.3M23.3 23.3l2.3 2.3M25.6 6.4l-2.3 2.3M8.7 23.3l-2.3 2.3" />
    </g>
    <circle cx="16" cy="16" r="6.6" fill="url(#{gradient})" />
  </svg>
  {#if wordmark}
    <span class="text-[1.05rem] font-semibold tracking-tight text-slate-50">Sorya</span>
  {/if}
</span>
