/**
 * Closing call to action: a "Follow" button bounces in, a finger taps it, and
 * it flips to a check mark. Following is what turns one viral video into an
 * audience, so the last seconds of every video ask for it.
 */
import React from 'react';
import { interpolate, spring } from 'remotion';
import type { PhaseTheme } from '../story';
import { fontFor } from '../story';

const LABELS: Record<string, { follow: string; line: string }> = {
  km: { follow: 'Follow', line: 'ចុច Follow ដើម្បីមើលរឿងបន្ទាប់!' },
  en: { follow: 'Follow', line: 'Follow for more!' }
};

export const FollowCta: React.FC<{
  frame: number;
  fps: number;
  start: number;
  language: string;
  theme: PhaseTheme;
  fontSize: number;
  /** Absolute position of the CTA block. */
  box: React.CSSProperties;
  /** Custom button label (e.g. "Shop now"); null keeps the "Follow" button and line. */
  label?: string | null;
}> = ({ frame, fps, start, language, theme, fontSize, box, label = null }) => {
  const age = frame - start;
  if (age < 0) return null;

  const base = LABELS[language.slice(0, 2)] ?? LABELS.en;
  // A custom label replaces both the button text and the "follow for more" line,
  // which would contradict a different call to action.
  const labels = label ? { follow: label, line: '' } : base;
  const enter = spring({ frame: age, fps, config: { damping: 10, stiffness: 180 } });
  const tapAt = Math.round(0.9 * fps);
  const tapped = age >= tapAt;
  const press = interpolate(age, [tapAt - 3, tapAt, tapAt + 4], [1, 0.9, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp'
  });
  const finger = interpolate(age, [4, tapAt - 2, tapAt, tapAt + 10], [140, 18, 8, 60], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp'
  });
  const ripple = interpolate(age, [tapAt, tapAt + 14], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        position: 'absolute',
        ...box,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: fontSize * 0.35,
        zIndex: 40,
        fontFamily: fontFor(language),
        transform: `scale(${enter})`
      }}
    >
      <div style={{ position: 'relative' }}>
        <div
          style={{
            position: 'absolute',
            inset: -fontSize * 0.4 * ripple,
            borderRadius: 999,
            border: `${fontSize * 0.08}px solid ${theme.accent}`,
            opacity: 1 - ripple
          }}
        />
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: fontSize * 0.35,
            padding: `${fontSize * 0.3}px ${fontSize * 0.7}px ${fontSize * 0.3}px ${fontSize * 0.32}px`,
            borderRadius: 999,
            background: tapped ? '#ffffff' : label ? theme.accent : '#fe2c55',
            color: tapped || label ? '#111018' : '#ffffff',
            fontSize,
            fontWeight: 900,
            transform: `scale(${press})`,
            boxShadow: '0 18px 50px rgba(0,0,0,.45)'
          }}
        >
          <span
            style={{
              display: 'grid',
              placeItems: 'center',
              width: fontSize * 1.2,
              height: fontSize * 1.2,
              borderRadius: '50%',
              background: tapped ? '#22c55e' : '#ffffff',
              color: tapped ? '#ffffff' : label ? theme.accent : '#fe2c55',
              fontFamily: "'Inter', system-ui, sans-serif",
              lineHeight: 1
            }}
          >
            {tapped ? '✓' : label ? '→' : '+'}
          </span>
          {labels.follow}
        </div>
        {/* Tapping finger. */}
        <svg
          viewBox="0 0 60 80"
          style={{
            position: 'absolute',
            width: fontSize * 1.1,
            right: -fontSize * 0.2,
            top: `${finger}%`,
            filter: 'drop-shadow(0 6px 10px rgba(0,0,0,.4))'
          }}
        >
          <path
            d="M22 6 C22 0 32 0 32 6 L32 34 L46 36 C54 38 56 44 54 52 L50 70 C49 76 44 78 38 78 L24 78 C18 78 14 74 12 68 L6 52 C4 46 10 42 15 47 L22 54 Z"
            fill="#ffe3c4"
            stroke="#1f1f1f"
            strokeWidth="3"
          />
        </svg>
      </div>
      <div
        style={{
          fontSize: fontSize * 0.7,
          fontWeight: 800,
          color: '#ffffff',
          textAlign: 'center',
          padding: `0 6%`,
          textShadow: '0 3px 0 #000, 0 0 18px rgba(0,0,0,.8)',
          opacity: interpolate(age, [6, 14], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
        }}
      >
        {labels.line}
      </div>
    </div>
  );
};
