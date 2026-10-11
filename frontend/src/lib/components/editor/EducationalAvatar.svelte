<script lang="ts">
  type Mood = 'hook' | 'setup' | 'rising' | 'twist' | 'climax' | 'payoff';
  let { speaking = false, mood = 'setup' }: { speaking?: boolean; mood?: Mood } = $props();
  const mouthHeight = $derived(speaking ? 20 : 7);
  const shirtColors: Record<Mood, [string, string]> = {
    hook: ['#ea580c', '#7c2d12'],
    setup: ['#2563eb', '#172554'],
    rising: ['#0d9488', '#134e4a'],
    twist: ['#9333ea', '#4c1d95'],
    climax: ['#dc2626', '#7f1d1d'],
    payoff: ['#f59e0b', '#92400e']
  };
  const colors = $derived(shirtColors[mood]);
  const raisedArm = $derived(['hook', 'twist', 'climax'].includes(mood));
  const browTilt = $derived(mood === 'twist' ? -8 : mood === 'climax' ? 7 : 0);
</script>

<svg viewBox="0 0 620 720" class="h-full w-full overflow-visible" aria-label="Educational presenter">
  <defs>
    <linearGradient id="preview-shirt" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color={colors[0]} />
      <stop offset="1" stop-color={colors[1]} />
    </linearGradient>
    <linearGradient id="preview-skin" x1="0" y1="0" x2="0.8" y2="1">
      <stop offset="0" stop-color="#fff4d8" />
      <stop offset="1" stop-color="#f6c98f" />
    </linearGradient>
    <filter id="preview-shadow" x="-40%" y="-40%" width="180%" height="180%">
      <feDropShadow dx="0" dy="18" stdDeviation="18" flood-color="#020617" flood-opacity="0.48" />
    </filter>
  </defs>

  <ellipse cx="310" cy="675" rx="205" ry="34" fill="#020617" opacity="0.4" />
  <path d="M145 690c12-145 58-230 165-230s153 85 165 230z" fill="url(#preview-shirt)" stroke="#60a5fa" stroke-width="7" filter="url(#preview-shadow)" />
  <path d="M242 475c20 35 116 35 136 0l20 32c-39 47-137 47-176 0z" fill="#0f172a" opacity="0.5" />
  <rect x="270" y="415" width="80" height="78" rx="35" fill="url(#preview-skin)" />
  <circle cx="310" cy="278" r="166" fill="url(#preview-skin)" stroke="#f59e0b" stroke-width="8" filter="url(#preview-shadow)" />
  <circle cx="151" cy="300" r="34" fill="#f5cb94" />
  <circle cx="469" cy="300" r="34" fill="#f5cb94" />
  <path d="M216 234q35-25 68 0" fill="none" stroke="#3f2d22" stroke-width="11" stroke-linecap="round" transform={`rotate(${browTilt} 250 234)`} />
  <path d="M336 234q35-25 68 0" fill="none" stroke="#3f2d22" stroke-width="11" stroke-linecap="round" transform={`rotate(${-browTilt} 370 234)`} />
  <ellipse cx="252" cy="276" rx="15" ry="27" fill="#171717" />
  <ellipse cx="368" cy="276" rx="15" ry="27" fill="#171717" />
  <circle cx="257" cy="268" r="5" fill="#fff" />
  <circle cx="373" cy="268" r="5" fill="#fff" />
  <path d="M300 298q10 13 22 0" fill="none" stroke="#d28c61" stroke-width="7" stroke-linecap="round" />
  <ellipse cx="310" cy="357" rx="62" ry={mouthHeight} fill="#641c2c" />
  {#if speaking}<path d="M260 350h100q-8 14-50 14t-50-14z" fill="#fff" />{/if}
  <path d={raisedArm ? 'M190 565q-70-62-90-132' : 'M190 565q-54 42-74 125'} fill="none" stroke={colors[0]} stroke-width="46" stroke-linecap="round" />
  <path d="M430 565q54 42 74 125" fill="none" stroke={colors[0]} stroke-width="46" stroke-linecap="round" />

  <g filter="url(#preview-shadow)">
    <path d="M18 516L164 428L283 452" fill="none" stroke="#111827" stroke-width="20" stroke-linecap="round" stroke-linejoin="round" />
    <circle cx="164" cy="428" r="18" fill="#334155" stroke="#94a3b8" stroke-width="5" />
    <circle cx="34" cy="505" r="18" fill="#334155" stroke="#94a3b8" stroke-width="5" />
    <g transform="translate(275 382) rotate(-5)">
      <rect width="76" height="150" rx="35" fill="#111827" stroke="#64748b" stroke-width="6" />
      <path d="M18 22h40M18 39h40M18 56h40" stroke="#475569" stroke-width="6" stroke-linecap="round" />
      <rect x="30" y="145" width="16" height="60" rx="8" fill="#0f172a" />
    </g>
  </g>
  {#if speaking}
    <g fill="none" stroke="#fbbf24" stroke-width="8" stroke-linecap="round" opacity="0.8">
      <path d="M372 412q28 24 0 48" />
      <path d="M392 394q49 43 0 84" />
    </g>
  {/if}
</svg>
