<script lang="ts">
  /**
   * One headline number: label, value, optional sub-line, optional state, optional trend.
   * `hero` is the single number a view leads with (48px+, same sans as everything).
   * A state always carries an icon AND a word: colour never says it alone.
   */
  import Icon from '$lib/components/ui/Icon.svelte';
  import Sparkline from '$lib/components/telemetry/Sparkline.svelte';

  type Tone = 'good' | 'warning' | 'serious' | 'critical';

  let {
    label,
    value,
    sub = undefined,
    state = undefined,
    trend = undefined,
    hero = false,
    stale = false
  }: {
    label: string;
    value: string;
    sub?: string;
    state?: { tone: Tone; label: string };
    trend?: number[];
    hero?: boolean;
    stale?: boolean;
  } = $props();

  const color: Record<Tone, string> = {
    good: 'var(--status-good)',
    warning: 'var(--status-warning)',
    serious: 'var(--status-serious)',
    critical: 'var(--status-critical)'
  };
</script>

<div
  class="flex min-w-0 flex-col justify-between gap-3 rounded-xl border border-slate-800 bg-[var(--viz-surface)] p-4 transition-opacity {stale
    ? 'opacity-50'
    : ''}"
>
  <div class="min-w-0">
    <p class="text-xs text-[var(--viz-ink-2)]">{label}</p>
    <p
      class="mt-1 font-semibold tracking-tight text-[var(--viz-ink)] {hero
        ? 'text-5xl leading-none'
        : 'text-2xl leading-tight'}"
    >
      {value}
    </p>
    {#if sub}<p class="mt-1 text-xs text-[var(--viz-ink-3)]">{sub}</p>{/if}
  </div>
  {#if state || trend}
    <div class="flex items-end justify-between gap-2">
      {#if state}
        <span class="inline-flex items-center gap-1.5 text-xs font-medium text-[var(--viz-ink-2)]">
          <span style="color:{color[state.tone]}">
            <Icon name={state.tone === 'good' ? 'check' : 'alert'} size={14} />
          </span>
          {state.label}
        </span>
      {:else}
        <span></span>
      {/if}
      {#if trend}<Sparkline values={trend} width={hero ? 260 : 96} height={hero ? 64 : 30} />{/if}
    </div>
  {/if}
</div>
