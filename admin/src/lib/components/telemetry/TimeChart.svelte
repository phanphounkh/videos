<script lang="ts" module>
  export type ChartSeries = {
    key: string;
    label: string;
    /** A CSS colour, normally a `var(--series-n)` / `var(--status-*)` token. */
    color: string;
    type: 'bar' | 'line';
    /** A faint wash under a line. */
    area?: boolean;
  };
  export type ChartPoint = { t: string } & Record<string, number | string | null>;
</script>

<script lang="ts">
  /**
   * A time series as bars and/or lines, on ONE value axis (never two).
   *
   * Marks follow the dataviz specs: bars at most 24px thick with a 4px rounded
   * data-end and square baseline, a 2px surface gap between stacked segments, 2px
   * round-joined lines with a marker of 8px or more ringed in the surface colour,
   * hairline solid gridlines. The pointer finds the nearest time (a crosshair) and
   * one tooltip lists every series; arrow keys do the same, and the table view
   * holds every number without hovering.
   */
  import ChartCard from '$lib/components/telemetry/ChartCard.svelte';
  import { compact, fullTime, niceTicks, timeLabel } from '$lib/components/telemetry/format';

  let {
    title,
    subtitle = undefined,
    points,
    series,
    format = compact,
    height = 210,
    stacked = true,
    stale = false,
    integers = true,
    emptyText = 'Nothing recorded in this range.'
  }: {
    title: string;
    subtitle?: string;
    points: ChartPoint[];
    series: ChartSeries[];
    format?: (value: number) => string;
    /** Bar series pile up into one column per time bucket. */
    stacked?: boolean;
    height?: number;
    stale?: boolean;
    /** Values are counts: axis ticks are whole numbers. Off for durations. */
    integers?: boolean;
    emptyText?: string;
  } = $props();

  const PAD = { l: 42, r: 10, t: 10, b: 26 };
  const GAP = 2; // surface gap between stacked segments
  const MAX_BAR = 24;

  let mode = $state<'chart' | 'table'>('chart');
  let width = $state(600);
  let hover = $state<number | null>(null);

  const n = $derived(points.length);
  const innerW = $derived(Math.max(0, width - PAD.l - PAD.r));
  const innerH = $derived(height - PAD.t - PAD.b);
  const band = $derived(innerW / Math.max(1, n));
  const bars = $derived(series.filter((s) => s.type === 'bar'));
  const lines = $derived(series.filter((s) => s.type === 'line'));

  const value = (point: ChartPoint, key: string): number | null => {
    const v = point[key];
    return typeof v === 'number' && Number.isFinite(v) ? v : null;
  };

  // The tallest thing drawn: a stacked column's total, or the biggest single value.
  const top = $derived.by(() => {
    let max = 0;
    for (const point of points) {
      const column = bars.reduce((sum, s) => sum + (value(point, s.key) ?? 0), 0);
      max = Math.max(max, stacked ? column : 0);
      for (const s of series) {
        if (!stacked || s.type === 'line') max = Math.max(max, value(point, s.key) ?? 0);
      }
    }
    return max;
  });
  const ticks = $derived(niceTicks(top, 4, integers));
  const ceiling = $derived(ticks[ticks.length - 1] || 1);
  const y = (v: number) => PAD.t + innerH - (v / ceiling) * innerH;
  const x = (i: number) => PAD.l + (i + 0.5) * band;
  const empty = $derived(top === 0);

  const span = $derived(
    n > 1 ? (new Date(points[n - 1].t).getTime() - new Date(points[0].t).getTime()) / 1000 : 0
  );
  const xLabels = $derived.by(() => {
    const target = Math.max(2, Math.floor(innerW / 96));
    const every = Math.max(1, Math.ceil(n / target));
    return points
      .map((p, i) => ({ i, label: timeLabel(p.t, span) }))
      .filter(({ i }) => i % every === 0 && x(i) < width - PAD.r - 20);
  });

  const barWidth = $derived(Math.max(1, Math.min(MAX_BAR, band * 0.72)));

  /** One bar segment: square at the baseline, 4px rounded at the data end. */
  function segment(cx: number, from: number, to: number, round: boolean): string {
    const w = barWidth;
    const left = cx - w / 2;
    const bottom = y(from);
    let topY = y(to);
    // A tiny value must still be visible.
    if (bottom - topY < 2) topY = bottom - 2;
    const r = round ? Math.min(4, w / 2, (bottom - topY) / 2) : 0;
    return `M${left},${bottom} V${topY + r} Q${left},${topY} ${left + r},${topY} H${left + w - r} Q${left + w},${topY} ${left + w},${topY + r} V${bottom} Z`;
  }

  /** The stacked segments of one column, lowest first. */
  function columns(point: ChartPoint, i: number) {
    const out: { key: string; color: string; d: string }[] = [];
    let base = 0;
    const present = bars.filter((s) => (value(point, s.key) ?? 0) > 0);
    present.forEach((s, index) => {
      const v = value(point, s.key) ?? 0;
      const from = stacked ? base : 0;
      const to = stacked ? base + v : v;
      // The gap goes between segments, never under the first one.
      const gap = stacked && index > 0 ? (GAP / innerH) * ceiling : 0;
      out.push({
        key: s.key,
        color: s.color,
        d: segment(x(i), from + gap, to, !stacked || index === present.length - 1)
      });
      base = to;
    });
    return out;
  }

  /** Line geometry, broken wherever a value is missing. */
  function path(key: string, close = false): string {
    const parts: string[] = [];
    let run: [number, number][] = [];
    const flush = () => {
      if (run.length > 1) {
        const line = run.map(([px, py], idx) => `${idx ? 'L' : 'M'}${px},${py}`).join(' ');
        parts.push(
          close
            ? `${line} L${run[run.length - 1][0]},${y(0)} L${run[0][0]},${y(0)} Z`
            : line
        );
      }
      run = [];
    };
    points.forEach((p, i) => {
      const v = value(p, key);
      if (v === null) flush();
      else run.push([x(i), y(v)]);
    });
    flush();
    return parts.join(' ');
  }

  function lastIndex(key: string): number {
    for (let i = n - 1; i >= 0; i--) if (value(points[i], key) !== null) return i;
    return -1;
  }

  // ---------------------------------------------------------------- pointer + keys
  function move(event: PointerEvent) {
    const rect = (event.currentTarget as SVGElement).getBoundingClientRect();
    hover = Math.min(n - 1, Math.max(0, Math.floor((event.clientX - rect.left - PAD.l) / band)));
  }

  function key(event: KeyboardEvent) {
    if (!n) return;
    const step = event.key === 'ArrowLeft' ? -1 : event.key === 'ArrowRight' ? 1 : 0;
    if (step === 0) {
      if (event.key === 'Escape') hover = null;
      return;
    }
    event.preventDefault();
    hover = Math.min(n - 1, Math.max(0, (hover ?? n - 1) + step));
  }

  const tipLeft = $derived(hover === null ? 0 : x(hover));
  const flip = $derived(hover !== null && x(hover) > width * 0.6);

  const summary = $derived(
    `${title}. ${series.map((s) => s.label).join(', ')}. ${n} time buckets. Use the Table view for every value.`
  );
</script>

<ChartCard {title} {subtitle} bind:mode {stale}>
  {#snippet chart()}
    {#if series.length > 1}
      <ul class="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--viz-ink-2)]">
        {#each series as s (s.key)}
          <li class="inline-flex items-center gap-1.5">
            {#if s.type === 'bar'}
              <span class="h-2.5 w-2.5 rounded-[3px]" style="background:{s.color}"></span>
            {:else}
              <span class="h-0.5 w-3.5 rounded" style="background:{s.color}"></span>
            {/if}
            {s.label}
          </li>
        {/each}
      </ul>
    {/if}

    <!-- Keyboard exploration of the chart (arrow keys move the crosshair), so this
         figure is focusable on purpose. -->
    <!-- svelte-ignore a11y_no_noninteractive_tabindex, a11y_no_noninteractive_element_interactions -->
    <div
      class="relative w-full min-w-0 select-none"
      style="height:{height}px"
      role="img"
      aria-label={summary}
      tabindex="0"
      bind:clientWidth={width}
      onkeydown={key}
      onfocus={() => (hover ??= n ? n - 1 : null)}
      onblur={() => (hover = null)}
    >
      <!-- absolute: the SVG must not set its container's width, or the chart could never shrink -->
      <svg {width} {height} class="absolute top-0 left-0 overflow-visible" aria-hidden="true">
        <!-- gridlines + value axis -->
        {#each ticks as tick (tick)}
          <line
            x1={PAD.l}
            x2={width - PAD.r}
            y1={y(tick)}
            y2={y(tick)}
            style="stroke:{tick === 0 ? 'var(--viz-axis)' : 'var(--viz-grid)'}"
            stroke-width="1"
          />
          <text
            x={PAD.l - 8}
            y={y(tick)}
            text-anchor="end"
            dominant-baseline="middle"
            class="fill-[var(--viz-ink-3)] text-[10px] tabular-nums">{format(tick)}</text
          >
        {/each}

        <!-- time axis -->
        {#each xLabels as { i, label } (i)}
          <text
            x={x(i)}
            y={height - 8}
            text-anchor="middle"
            class="fill-[var(--viz-ink-3)] text-[10px] tabular-nums">{label}</text
          >
        {/each}

        {#if !empty}
          <!-- bars -->
          {#each points as point, i (point.t)}
            {#each columns(point, i) as seg (seg.key)}
              <path
                d={seg.d}
                style="fill:{seg.color}"
                opacity={hover === null || hover === i ? 1 : 0.55}
              />
            {/each}
          {/each}

          <!-- lines -->
          {#each lines as s (s.key)}
            {#if s.area}
              <path d={path(s.key, true)} style="fill:{s.color}" opacity="0.1" />
            {/if}
            <path
              d={path(s.key)}
              fill="none"
              style="stroke:{s.color}"
              stroke-width="2"
              stroke-linejoin="round"
              stroke-linecap="round"
            />
            {@const end = hover ?? lastIndex(s.key)}
            {#if end >= 0 && value(points[end], s.key) !== null}
              <circle
                cx={x(end)}
                cy={y(value(points[end], s.key) ?? 0)}
                r="4.5"
                style="fill:{s.color}; stroke:var(--viz-surface)"
                stroke-width="2"
              />
            {/if}
          {/each}
        {/if}

        <!-- crosshair -->
        {#if hover !== null && !empty}
          <line
            x1={x(hover)}
            x2={x(hover)}
            y1={PAD.t}
            y2={PAD.t + innerH}
            style="stroke:var(--viz-crosshair)"
            stroke-width="1"
          />
        {/if}

        <!-- the whole plot is the hit target, so the pointer only needs to be near;
           the same values are reachable by keyboard and in the table view -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <rect
          x={PAD.l}
          y={PAD.t}
          width={innerW}
          height={innerH}
          fill="transparent"
          onpointermove={move}
          onpointerleave={() => (hover = null)}
        />
      </svg>

      {#if empty}
        <p
          class="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 text-center text-xs text-[var(--viz-ink-3)]"
          style="padding-left:{PAD.l}px"
        >
          {emptyText}
        </p>
      {/if}

      {#if hover !== null && !empty && points[hover]}
        <div
          class="pointer-events-none absolute z-10 min-w-36 rounded-lg border border-slate-700 bg-slate-950/95 px-3 py-2 text-xs shadow-pop backdrop-blur"
          style="top:{PAD.t}px; {flip ? `right:${width - tipLeft + 12}px` : `left:${tipLeft + 12}px`}"
        >
          <p class="mb-1 text-[var(--viz-ink-3)]">{fullTime(points[hover].t)}</p>
          {#each series as s (s.key)}
            {@const v = value(points[hover], s.key)}
            <p class="flex items-center gap-2 py-0.5">
              <span class="h-[3px] w-2.5 shrink-0 rounded" style="background:{s.color}"></span>
              <span class="font-semibold text-[var(--viz-ink)] tabular-nums">{v === null ? '–' : format(v)}</span>
              <span class="text-[var(--viz-ink-2)]">{s.label}</span>
            </p>
          {/each}
        </div>
      {/if}
    </div>
  {/snippet}

  {#snippet table()}
    <div class="max-h-64 overflow-auto rounded-lg border border-slate-800">
      <table class="w-full text-left text-xs">
        <thead class="sticky top-0 bg-slate-900 text-[var(--viz-ink-3)]">
          <tr>
            <th class="px-3 py-2 font-medium">Time</th>
            {#each series as s (s.key)}<th class="px-3 py-2 text-right font-medium">{s.label}</th>{/each}
          </tr>
        </thead>
        <tbody class="text-[var(--viz-ink)] tabular-nums">
          {#each points as point (point.t)}
            <tr class="border-t border-slate-800/70">
              <td class="px-3 py-1.5 text-[var(--viz-ink-2)]">{fullTime(point.t)}</td>
              {#each series as s (s.key)}
                {@const v = value(point, s.key)}
                <td class="px-3 py-1.5 text-right">{v === null ? '–' : format(v)}</td>
              {/each}
            </tr>
          {/each}
        </tbody>
      </table>
    </div>
  {/snippet}
</ChartCard>
