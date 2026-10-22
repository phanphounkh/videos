/**
 * How a text or sticker layer looks, as plain CSS.
 *
 * Shared by the renderer and by the editor's on-canvas overlay, so the box you
 * drag in the preview is the box that ends up in the exported video. Sizes are
 * in COMPOSITION pixels; the editor scales the whole overlay to fit the player.
 */
import type React from 'react';
import type { Layer } from './schema';
import { fontFor } from './story';

const KHMER = /[ក-៿]/;

/** A Khmer word in an English video still needs a Khmer font. */
export const fontForText = (text: string, language: string): string =>
  KHMER.test(text) ? fontFor('km') : fontFor(language);

const EMOJI_FONT = "'Noto Color Emoji', 'Apple Color Emoji', 'Segoe UI Emoji'";

/** Position and rotation: the layer's centre sits at (x%, y%). */
export const layerPlacement = (layer: Layer): React.CSSProperties => ({
  position: 'absolute',
  left: `${layer.x}%`,
  top: `${layer.y}%`
});

/** The text itself: size, colour, weight, optional background pill. */
export const layerTextStyle = (layer: Layer, width: number, height: number, language: string): React.CSSProperties => {
  const short = Math.min(width, height);
  const size = (short * layer.fontSize) / 100;
  const sticker = layer.type === 'sticker';
  return {
    width: 'max-content',
    maxWidth: width * 0.9,
    fontFamily: sticker ? `${EMOJI_FONT}, sans-serif` : fontForText(layer.text, language),
    fontSize: size,
    fontWeight: layer.weight,
    lineHeight: sticker ? 1.05 : KHMER.test(layer.text) ? 1.6 : 1.15,
    color: layer.color,
    textAlign: 'center',
    whiteSpace: 'pre-wrap',
    overflowWrap: 'anywhere',
    ...(layer.background && !sticker
      ? { background: layer.background, padding: '0.22em 0.55em', borderRadius: '0.4em' }
      : sticker
        ? {}
        : {
            // Readable on any picture without a background.
            textShadow: `0 ${size * 0.04}px 0 rgba(0,0,0,.75), 0 0 ${size * 0.3}px rgba(0,0,0,.65)`
          })
  };
};
