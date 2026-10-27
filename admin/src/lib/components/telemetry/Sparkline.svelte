<script lang="ts">
  /**
   * A 12-point trend: the history in the quiet de-emphasis colour, the current
   * (last) point in the accent with a ringed marker. It has no axis because it makes
   * no claim about scale: the tile's number is the value, this is only the shape.
   */
  let {
    values,
    color = 'var(--series-1)',
    width = 96,
    height = 30
  }: { values: number[]; color?: string; width?: number; height?: number } = $props();

  const PAD = 5; // room for the marker's radius and its ring
  const max = $derived(Math.max(...values, 0));
  const min = $derived(Math.min(...values, 0));
  const points = $derived(
    values.map((v, i) => [
      PAD + (values.length > 1 ? (i / (values.length - 1)) * (width - 2 * PAD) : (width - 2 * PAD) / 2),
      height - PAD - (max === min ? 0 : ((v - min) / (max - min)) * (height - 2 * PAD))
    ])
  );
  const line = $derived(points.map(([px, py], i) => `${i ? 'L' : 'M'}${px},${py}`).join(' '));
  const last = $derived(points[points.length - 1]);
</script>

{#if values.length > 1 && max > 0}
  <svg {width} {height} class="block overflow-visible" aria-hidden="true">
    <path
      d={line}
      fill="none"
      stroke="var(--viz-crosshair)"
      stroke-width="2"
      stroke-linejoin="round"
      stroke-linecap="round"
    />
    {#if points.length > 1}
      <path
        d={`M${points[points.length - 2][0]},${points[points.length - 2][1]} L${last[0]},${last[1]}`}
        fill="none"
        style="stroke:{color}"
        stroke-width="2"
        stroke-linecap="round"
      />
    {/if}
    <circle cx={last[0]} cy={last[1]} r="4" style="fill:{color}; stroke:var(--viz-surface)" stroke-width="2" />
  </svg>
{:else}
  <span class="block" style="width:{width}px; height:{height}px" aria-hidden="true"></span>
{/if}
