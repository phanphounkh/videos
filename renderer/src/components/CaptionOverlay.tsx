/**
 * Short-video captions: big, outlined, a few words at a time, with the word
 * being spoken highlighted (karaoke style).
 *
 * Khmer note: Khmer has no spaces between words, so the caption is split into
 * words with Intl.Segmenter (Chromium ships a Khmer word dictionary) and never
 * on whitespace or raw character index. If the segmenter is unavailable the
 * whole caption is treated as one unit, which still reads correctly.
 *
 * Highlight timing uses the TTS speech marks when the scene has them, and
 * otherwise spreads the caption's time over its words by length.
 */
import React, { useMemo } from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import type { Caption, Word } from '../schema';
import { fontFor } from '../story';

type Unit = { text: string; start: number; end: number };

const segmentWords = (text: string, language: string): string[] => {
  const Segmenter = (Intl as unknown as { Segmenter?: new (l: string, o: object) => { segment: (t: string) => Iterable<{ segment: string }> } }).Segmenter;
  if (!language.startsWith('km')) return text.split(/\s+/).filter(Boolean);
  if (!Segmenter) return [text];
  // Keep punctuation and spaces attached to the word before them.
  const units: string[] = [];
  for (const { segment } of new Segmenter(language, { granularity: 'word' }).segment(text)) {
    if (units.length > 0 && !/[ក-៝0-9A-Za-z]/.test(segment)) units[units.length - 1] += segment;
    else units.push(segment);
  }
  return units.filter((unit) => unit.trim());
};

const unitsFor = (caption: Caption, words: Word[], language: string): Unit[] => {
  const parts = segmentWords(caption.text, language);
  // When the provider's marks line up one-to-one with this caption's words
  // (English), use them directly.
  const inside = words.filter((w) => w.start >= caption.start - 0.02 && w.start < caption.end);
  if (inside.length === parts.length && inside.length > 0) {
    return parts.map((text, i) => ({ text, start: inside[i].start, end: inside[i].end }));
  }
  // Otherwise spread the spoken part of the caption over its words by length.
  // The caption can stay on screen through a pause, so stop at the last mark.
  const spoken = words.filter((w) => w.start < caption.end && w.end > caption.start);
  const speechEnd = spoken.length > 0 ? Math.min(caption.end, Math.max(...spoken.map((w) => w.end))) : caption.end;
  const end = Math.max(caption.start + 0.2, speechEnd);
  const total = parts.reduce((sum, p) => sum + p.length, 0) || 1;
  let cursor = caption.start;
  return parts.map((text) => {
    const span = ((end - caption.start) * text.length) / total;
    const unit = { text, start: cursor, end: cursor + span };
    cursor += span;
    return unit;
  });
};

/** A thick dark outline built from shadows, so Khmer stacked glyphs stay intact. */
const outline = (radius: number, color: string): string => {
  const steps = 16;
  const rings: string[] = [];
  for (let i = 0; i < steps; i++) {
    const angle = (i / steps) * Math.PI * 2;
    rings.push(`${(Math.cos(angle) * radius).toFixed(1)}px ${(Math.sin(angle) * radius).toFixed(1)}px 0 ${color}`);
  }
  return [...rings, `0 ${radius * 1.6}px ${radius * 2}px rgba(0,0,0,.55)`].join(',');
};

export const CaptionOverlay: React.FC<{
  captions: Caption[];
  words: Word[];
  language: string;
  accent: string;
  /** Vertical centre of the caption block, as a fraction of the frame height. */
  centerY: number;
}> = ({ captions, words, language, accent, centerY }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const time = frame / fps;
  const isKhmer = language.startsWith('km');

  const index = captions.findIndex((c) => time >= c.start && time < c.end);
  const active = index >= 0 ? captions[index] : null;
  const units = useMemo(() => (active ? unitsFor(active, words, language) : []), [active, words, language]);
  if (!active) return null;

  const short = Math.min(width, height);
  const fontSize = short * (isKhmer ? 0.064 : 0.074);
  const appear = spring({
    frame: frame - Math.round(active.start * fps),
    fps,
    config: { damping: 14, stiffness: 260, mass: 0.6 }
  });

  return (
    <div
      style={{
        position: 'absolute',
        left: '7%',
        right: '7%',
        top: `${centerY * 100}%`,
        transform: `translateY(-50%) scale(${0.82 + 0.18 * appear})`,
        opacity: Math.min(1, appear * 1.6),
        textAlign: 'center',
        zIndex: 30,
        fontFamily: fontFor(language),
        fontSize,
        fontWeight: 900,
        lineHeight: isKhmer ? 1.65 : 1.12,
        letterSpacing: isKhmer ? 0 : '-0.01em',
        textTransform: isKhmer ? 'none' : 'uppercase',
        color: '#ffffff',
        textShadow: outline(fontSize * 0.085, '#0a0a0f')
      }}
    >
      {units.map((unit, i) => {
        const now = time >= unit.start && time < unit.end;
        const pop = now
          ? interpolate(time - unit.start, [0, 0.08, 0.2], [1, 1.14, 1.06], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp'
            })
          : 1;
        return (
          <span
            key={`${index}-${i}`}
            style={{
              display: 'inline-block',
              margin: isKhmer ? '0 0.04em' : '0 0.16em',
              color: now ? accent : '#ffffff',
              transform: `scale(${pop}) rotate(${now ? -2 : 0}deg)`
            }}
          >
            {unit.text}
          </span>
        );
      })}
    </div>
  );
};
