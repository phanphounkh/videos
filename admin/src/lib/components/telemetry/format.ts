/** Number and time formatting for the dashboard. All pure, so they can be tested. */

/** 1,284 / 12.9K / 4.2M: compact from 1,000 up. */
export function compact(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value))
    return "–";
  const abs = Math.abs(value);
  if (abs >= 1_000_000) return `${trim(value / 1_000_000)}M`;
  if (abs >= 1_000) return `${trim(value / 1_000)}K`;
  return Number.isInteger(value) ? String(value) : trim(value);
}

const trim = (n: number): string => {
  const rounded = Math.abs(n) >= 100 ? Math.round(n) : Math.round(n * 10) / 10;
  return String(rounded);
};

/** 420 ms / 1.3 s / 2m 05s */
export function duration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return "–";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = ms / 1000;
  if (seconds < 60)
    return `${seconds < 10 ? seconds.toFixed(1) : Math.round(seconds)} s`;
  const m = Math.floor(seconds / 60);
  return `${m}m ${String(Math.round(seconds - m * 60)).padStart(2, "0")}s`;
}

export function percent(
  fraction: number | null | undefined,
  digits = 1,
): string {
  if (fraction === null || fraction === undefined || !Number.isFinite(fraction))
    return "–";
  const value = fraction * 100;
  return `${value === 0 || value >= 10 ? Math.round(value) : value.toFixed(digits)}%`;
}

export function usd(value: number | null | undefined): string {
  if (value === null || value === undefined) return "–";
  if (value === 0) return "$0";
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(value < 100 ? 2 : 0)}`;
}

/** "3 min ago", "2 h ago", or a date for anything older than two days. */
export function ago(iso: string, now = Date.now()): string {
  const seconds = Math.max(0, (now - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)} min ago`;
  if (seconds < 86_400) return `${Math.floor(seconds / 3600)} h ago`;
  if (seconds < 172_800) return "yesterday";
  return new Date(iso).toLocaleDateString([], {
    month: "short",
    day: "numeric",
  });
}

/** Axis label for a bucket: a time of day for short windows, a date for long ones. */
export function timeLabel(iso: string, spanSeconds: number): string {
  const date = new Date(iso);
  return spanSeconds <= 2 * 86_400
    ? date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString([], { month: "short", day: "numeric" });
}

/** Full label for a tooltip header. */
export function fullTime(iso: string): string {
  return new Date(iso).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * Round tick values for an axis from 0 to just above `max`: 0, 50, 100, 150...
 * Steps are 1, 2 or 5 times a power of ten, so labels are always clean numbers.
 */
export function niceTicks(max: number, target = 4, integers = false): number[] {
  if (!Number.isFinite(max) || max <= 0) return [0, 1];
  const rough = max / target;
  const power = 10 ** Math.floor(Math.log10(rough));
  let step =
    [1, 2, 5, 10].map((m) => m * power).find((s) => s >= rough) ?? power * 10;
  // Counts are whole numbers: an axis must never say "0.5 errors".
  if (integers) step = Math.max(1, Math.round(step));
  const ticks: number[] = [];
  for (let value = 0; value < max + step * 0.999; value += step) {
    ticks.push(Math.round(value * 1e9) / 1e9);
    if (ticks.length > 12) break;
  }
  return ticks;
}

/** Health tone from a value and its two thresholds (lower is better). */
export function tone(
  value: number | null,
  good: number,
  poor: number,
): "good" | "warning" | "critical" | null {
  if (value === null) return null;
  return value <= good ? "good" : value <= poor ? "warning" : "critical";
}

/** The sparkline's 12 points: the series folded into equal groups. */
export function fold(values: number[], parts = 12): number[] {
  if (values.length <= parts) return values;
  const size = values.length / parts;
  return Array.from({ length: parts }, (_, i) =>
    values
      .slice(Math.floor(i * size), Math.floor((i + 1) * size))
      .reduce((a, b) => a + b, 0),
  );
}
