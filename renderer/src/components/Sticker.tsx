/**
 * The scene's key point as a punchy sticker: it slams in with an overshoot and
 * a burst of rays, floats while it is read, then shrinks away.
 */
import React from 'react';
import { interpolate, spring } from 'remotion';
import type { PhaseTheme } from '../story';
import { fontFor } from '../story';

export const Sticker: React.FC<{
  text: string;
  theme: PhaseTheme;
  language: string;
  frame: number;
  fps: number;
  window: { start: number; end: number };
  /** Absolute position of the sticker's box. */
  box: React.CSSProperties;
  fontSize: number;
  /** The hook sticker is bigger and shakes for attention. */
  loud: boolean;
}> = ({ text, theme, language, frame, fps, window, box, fontSize, loud }) => {
  const age = frame - window.start;
  if (age < 0 || frame > window.end) return null;

  const isKhmer = language.startsWith('km');
  const enter = spring({ frame: age, fps, config: { damping: 9, stiffness: 210, mass: 0.7 } });
  const exit = interpolate(frame, [window.end - 7, window.end], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp'
  });
  const shake = loud && age < 14 ? Math.sin(age * 2.4) * (14 - age) * 0.6 : 0;
  const float = Math.sin((age / fps) * 2.2) * 6;
  const rotate = -3 + (1 - enter) * -14 + shake * 0.4;
  const burst = interpolate(age, [0, 14], [0, 1], { extrapolateRight: 'clamp' });

  return (
    <div
      style={{
        position: 'absolute',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 20,
        ...box
      }}
    >
      {/* Burst rays, behind the sticker. */}
      <svg
        viewBox="-100 -100 200 200"
        style={{ position: 'absolute', width: '130%', aspectRatio: '1', opacity: 1 - burst, overflow: 'visible' }}
      >
        {Array.from({ length: 12 }, (_, i) => {
          const angle = (i / 12) * Math.PI * 2;
          const r1 = 30 + burst * 40;
          const r2 = r1 + 12 + (i % 2) * 10;
          return (
            <line
              key={i}
              x1={Math.cos(angle) * r1}
              y1={Math.sin(angle) * r1 * 0.6}
              x2={Math.cos(angle) * r2}
              y2={Math.sin(angle) * r2 * 0.6}
              stroke={i % 2 ? '#ffffff' : theme.accent}
              strokeWidth={4}
              strokeLinecap="round"
            />
          );
        })}
      </svg>

      <div
        style={{
          transform: `translate(${shake}px, ${float}px) scale(${enter * exit}) rotate(${rotate}deg)`,
          opacity: exit,
          padding: isKhmer ? '0.25em 0.8em 0.32em' : '0.38em 0.8em',
          borderRadius: '0.6em',
          background: `linear-gradient(135deg, ${theme.accent} 0%, #ffffff 160%)`,
          border: `${Math.max(4, fontSize * 0.08)}px solid #ffffff`,
          boxShadow: `0 ${fontSize * 0.3}px 0 ${theme.shade}, 0 ${fontSize * 0.6}px ${fontSize * 1.2}px rgba(0,0,0,.45)`,
          color: '#111018',
          fontFamily: fontFor(language),
          fontSize,
          fontWeight: 900,
          lineHeight: isKhmer ? 1.6 : 1.08,
          letterSpacing: isKhmer ? 0 : '-0.02em',
          textTransform: isKhmer ? 'none' : 'uppercase',
          textAlign: 'center',
          maxWidth: '100%'
        }}
      >
        {text}
      </div>
    </div>
  );
};
