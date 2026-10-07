/**
 * Draws the caption that is active at the current frame.
 *
 * Khmer note: Khmer has no spaces between words, so we never split caption text
 * on whitespace here. The backend decides the caption segments; the renderer
 * only positions whatever string it is given, with a Khmer-capable font.
 */
import React from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import type { Caption } from '../schema';

export const CaptionOverlay: React.FC<{ captions: Caption[]; language: string }> = ({
  captions,
  language
}) => {
  const frame = useCurrentFrame();
  const { fps, height } = useVideoConfig();
  const time = frame / fps;

  const active = captions.find((c) => time >= c.start && time < c.end);
  if (!active) return null;

  const isKhmer = language.startsWith('km');

  return (
    <div
      style={{
        position: 'absolute',
        bottom: height * 0.08,
        left: '8%',
        right: '8%',
        textAlign: 'center'
      }}
    >
      <span
        style={{
          display: 'inline-block',
          padding: '14px 26px',
          borderRadius: 14,
          backgroundColor: 'rgba(0,0,0,0.65)',
          color: '#ffffff',
          fontSize: isKhmer ? 48 : 54,
          lineHeight: isKhmer ? 1.8 : 1.3,
          fontWeight: 600,
          fontFamily: isKhmer
            ? "'Noto Sans Khmer', 'Khmer OS', sans-serif"
            : "'Inter', system-ui, sans-serif"
        }}
      >
        {active.text}
      </span>
    </div>
  );
};
