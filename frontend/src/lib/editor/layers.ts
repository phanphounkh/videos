/** Helpers for text and sticker layers. */
import type { Layer as RenderLayer } from '$renderer/schema';
import type { Layer, Scene } from '$lib/types/api';

/** The renderer spells it fontSize; the API font_size. */
export const toRenderLayer = (layer: Layer): RenderLayer => ({
  id: layer.id,
  type: layer.type,
  text: layer.text,
  x: layer.x,
  y: layer.y,
  fontSize: layer.font_size,
  rotation: layer.rotation,
  color: layer.color,
  background: layer.background,
  weight: layer.weight,
  animation: layer.animation,
  start: layer.start,
  end: layer.end
});

export const newId = (): string =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID().slice(0, 12)
    : Math.random().toString(36).slice(2, 14);

export const STICKERS = [
  '🔥', '⭐', '❤️', '👍', '👏', '🎉', '😂', '😍', '🤯', '😎', '🙌', '💡',
  '✅', '❌', '⚡', '🚀', '💰', '🎯', '📣', '👀', '🏆', '🌟', '➡️', '⬇️'
];

/** A new layer centred on the frame, visible for the whole scene (max 4s). */
export const makeLayer = (
  kind: 'text' | 'sticker',
  scene: Scene,
  at = 0,
  language = 'en'
): Layer => {
  const start = Math.min(Math.max(0, at), Math.max(0, scene.duration - 0.5));
  const end = Math.min(scene.duration, start + 4);
  return {
    id: newId(),
    type: kind,
    text: kind === 'sticker' ? '🔥' : language.startsWith('km') ? 'អត្ថបទ' : 'Your text',
    x: 50,
    y: kind === 'sticker' ? 35 : 50,
    font_size: kind === 'sticker' ? 14 : 8,
    rotation: 0,
    color: '#ffffff',
    background: null,
    weight: 800,
    animation: 'pop',
    start,
    end
  };
};

export const layersOf = (scene: Scene): Layer[] =>
  ((scene.settings?.layers as Layer[] | undefined) ?? []).map((layer) => ({ ...layer }));

export const round = (value: number, digits = 2): number => {
  const k = 10 ** digits;
  return Math.round(value * k) / k;
};

export const clamp = (value: number, low: number, high: number): number =>
  Math.min(high, Math.max(low, value));

const UNITLESS = new Set(['font-weight', 'line-height', 'opacity', 'z-index']);

/** A React-style CSS object as a style attribute: camelCase -> kebab-case, numbers -> px. */
export const cssText = (style: object): string =>
  (Object.entries(style) as [string, string | number | undefined][])
    .filter(([, value]) => value !== undefined)
    .map(([key, value]) => {
      const name = key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
      return `${name}:${typeof value === 'number' && !UNITLESS.has(name) ? `${value}px` : value}`;
    })
    .join(';');
