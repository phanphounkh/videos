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
        bottom: height * 0.025,
        left: '6%',
        right: '6%',
        textAlign: 'center',
        zIndex: 30
      }}
    >
      <span
        style={{
          display: 'inline-block',
          padding: '13px 28px',
          borderRadius: 14,
          backgroundColor: 'rgba(2,6,23,0.92)',
          border: '1px solid rgba(255,255,255,.12)',
          boxShadow: '0 14px 35px rgba(2,6,23,.5)',
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
