/**
 * The built-in hosts ("avatars").
 *
 * Twelve of them: two STYLES (cartoon "toon" and semi-realistic illustrated "real"),
 * each in male/female x young/adult/old. A look is a plain parametric description: the
 * cartoon and the realistic component each draw it in their own way, so adding a host
 * is data, not drawing code.
 *
 * `toon-m-young` is the original presenter and MUST keep rendering exactly as it always
 * did (existing projects depend on it); its look below is the old hard-coded one.
 */

export type AvatarStyle = 'toon' | 'real';
export type Gender = 'male' | 'female';
export type Age = 'young' | 'adult' | 'old';

export type HairStyle =
  | 'short' // short with a cowlick (toon) / textured crop (real)
  | 'sidepart' // neat side parting
  | 'cropped' // very short
  | 'balding' // bald crown, hair only at the sides
  | 'bob' // chin-length
  | 'long' // long and straight
  | 'wavy' // shoulder length, wavy
  | 'ponytail'
  | 'bun';

export type FacialHair = 'none' | 'stubble' | 'mustache' | 'goatee' | 'beard';
export type OutfitKind = 'tee' | 'collar' | 'scoop' | 'blazer' | 'cardigan' | 'blouse';

export type AvatarLook = {
  /** Skin base, highlight and shadow/outline colours. */
  skin: string;
  skinLight: string;
  skinLine: string;
  /** Cheek blush. */
  blush: string;
  hair: string;
  hairHi: string;
  /** Eyebrow colour. */
  brow: string;
  eye: string;
  /** Lip colour (real style) and lipstick (toon females). null = natural / no lipstick. */
  lip: string | null;
  hairStyle: HairStyle;
  /** Toon only: the bouncing tuft of the original host. */
  cowlick: boolean;
  facialHair: FacialHair;
  beard: string;
  glasses: { color: string; shape: 'round' | 'square' } | null;
  /** 0..1 age lines: forehead, crow's feet, laugh lines. */
  wrinkles: number;
  /** Multipliers on the eyes (1 = the original host). */
  eyeScale: number;
  /** Face proportions, 1 = default. */
  faceWidth: number;
  faceLength: number;
  lashes: boolean;
  earrings: boolean;
  /** Necklace colour; null = none. */
  necklace: string | null;
  outfit: {
    kind: OutfitKind;
    /** Main garment colour; null = the story theme's gradient (toon only). */
    color: string | null;
    /** Collar / inner shirt colour. */
    inner: string;
  };
  /** Shoulder width. */
  build: 'slim' | 'regular' | 'broad';
  /** Thickness of the brows (toon). */
  browWeight: number;
};

export type AvatarSpec = {
  id: string;
  name: string;
  style: AvatarStyle;
  gender: Gender;
  age: Age;
  look: AvatarLook;
};

export const DEFAULT_AVATAR_ID = 'toon-m-young';

export const mixHex = (a: string, b: string, t: number): string => {
  const p = (hex: string) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  const [r1, g1, b1] = p(a);
  const [r2, g2, b2] = p(b);
  const h = (x: number, y: number) => Math.round(x + (y - x) * t).toString(16).padStart(2, '0');
  return `#${h(r1, r2)}${h(g1, g2)}${h(b1, b2)}`;
};

/** Highlight and shadow colours that stay warm for any base skin tone. */
const tone = (skin: string) => ({
  skin,
  skinLight: mixHex(skin, '#fff4e6', 0.45),
  skinLine: mixHex(skin, '#6b2f12', 0.42)
});

const BASE: AvatarLook = {
  ...tone('#f6c79a'),
  blush: '#fb7185',
  hair: '#24160f',
  hairHi: '#4a3326',
  brow: '#24160f',
  eye: '#4a2a18',
  lip: null,
  hairStyle: 'short',
  cowlick: false,
  facialHair: 'none',
  beard: '#24160f',
  glasses: null,
  wrinkles: 0,
  eyeScale: 1,
  faceWidth: 1,
  faceLength: 1,
  lashes: false,
  earrings: false,
  necklace: null,
  outfit: { kind: 'tee', color: null, inner: '#ffffff' },
  build: 'regular',
  browWeight: 13
};

const look = (patch: Partial<AvatarLook> & { skinBase?: string }): AvatarLook => {
  const { skinBase, ...rest } = patch;
  return { ...BASE, ...(skinBase ? tone(skinBase) : {}), ...rest };
};

const GRAY = { hair: '#c9ccd2', hairHi: '#f1f2f5', brow: '#aeb2ba', beard: '#e4e6ea' };
const WHITE = { hair: '#e6e8ec', hairHi: '#ffffff', brow: '#c3c7ce', beard: '#f3f4f6' };

export const BUILTIN_AVATARS: AvatarSpec[] = [
  // ---- cartoon ------------------------------------------------------------
  {
    id: 'toon-m-young', name: 'Dara', style: 'toon', gender: 'male', age: 'young',
    // The original host, exactly.
    look: look({ cowlick: true, skin: '#f6c79a', skinLight: '#ffe3c4', skinLine: '#c98a5c' })
  },
  {
    id: 'toon-f-young', name: 'Sophea', style: 'toon', gender: 'female', age: 'young',
    look: look({
      skinBase: '#f3c4a0', hair: '#1b1210', hairHi: '#3c2a24', brow: '#1b1210', hairStyle: 'ponytail',
      eyeScale: 1.1, faceWidth: 0.97, lashes: true, lip: '#e5527a', blush: '#f9739a', browWeight: 9,
      outfit: { kind: 'scoop', color: null, inner: '#ffffff' }, build: 'slim', earrings: true
    })
  },
  {
    id: 'toon-m-adult', name: 'Vuthy', style: 'toon', gender: 'male', age: 'adult',
    look: look({
      skinBase: '#d8a06f', hair: '#1c120d', hairHi: '#3a2a20', brow: '#1c120d', hairStyle: 'sidepart',
      facialHair: 'mustache', beard: '#1c120d', eyeScale: 0.9, faceWidth: 1.02, faceLength: 1.02, wrinkles: 0.25,
      browWeight: 15, outfit: { kind: 'blazer', color: '#27364f', inner: '#f4f6fa' }, build: 'broad',
      eye: '#3a2012', blush: '#d97b5b'
    })
  },
  {
    id: 'toon-f-adult', name: 'Chenda', style: 'toon', gender: 'female', age: 'adult',
    look: look({
      skinBase: '#e8b88c', hair: '#2a1710', hairHi: '#55382a', brow: '#2a1710', hairStyle: 'bob',
      eyeScale: 0.96, faceWidth: 0.98, lashes: true, lip: '#b8324f', blush: '#f06a82', browWeight: 9, wrinkles: 0.1,
      glasses: { color: '#7c2d4e', shape: 'round' }, earrings: true,
      outfit: { kind: 'blazer', color: '#7a2447', inner: '#fbeef3' }, build: 'slim'
    })
  },
  {
    id: 'toon-m-old', name: 'Ta Sok', style: 'toon', gender: 'male', age: 'old',
    look: look({
      skinBase: '#c58a5c', ...WHITE, hairStyle: 'balding', facialHair: 'beard', eyeScale: 0.8, faceWidth: 1.0,
      faceLength: 1.03, wrinkles: 0.9, glasses: { color: '#5b3a1f', shape: 'square' }, browWeight: 16,
      outfit: { kind: 'cardigan', color: '#6b5a3a', inner: '#e8e2d2' }, build: 'regular', blush: '#c9715a',
      eye: '#3a2012'
    })
  },
  {
    id: 'toon-f-old', name: 'Yeay Sarun', style: 'toon', gender: 'female', age: 'old',
    look: look({
      skinBase: '#d9a67e', ...GRAY, hairStyle: 'bun', eyeScale: 0.82, faceWidth: 0.98, faceLength: 1.02,
      wrinkles: 0.8, lashes: false, lip: '#c4566b', blush: '#e48a8a', browWeight: 8,
      glasses: { color: '#a8863a', shape: 'round' }, earrings: false, necklace: '#f4ead2',
      outfit: { kind: 'cardigan', color: '#7b4a8a', inner: '#f4ead2' }, build: 'slim', eye: '#3a2012'
    })
  },
  // ---- semi-realistic -------------------------------------------------------
  {
    id: 'real-m-young', name: 'Rithy', style: 'real', gender: 'male', age: 'young',
    look: look({
      skinBase: '#dcab7c', hair: '#17110e', hairHi: '#4a3a30', brow: '#1d1410', hairStyle: 'short', eye: '#3a2216',
      lip: '#b9766a', outfit: { kind: 'blazer', color: '#2f4a6b', inner: '#f1f3f7' }, build: 'regular', wrinkles: 0,
      blush: '#e08a78'
    })
  },
  {
    id: 'real-f-young', name: 'Maly', style: 'real', gender: 'female', age: 'young',
    look: look({
      skinBase: '#f1cba8', hair: '#140e0c', hairHi: '#4d3a34', brow: '#1d1410', hairStyle: 'long', eye: '#33200f',
      lip: '#c4566a', lashes: true, earrings: true, outfit: { kind: 'blouse', color: '#c0507a', inner: '#fff1f5' },
      build: 'slim', blush: '#f09aa0'
    })
  },
  {
    id: 'real-m-adult', name: 'Samnang', style: 'real', gender: 'male', age: 'adult',
    look: look({
      skinBase: '#b98258', hair: '#1a110c', hairHi: '#443126', brow: '#1a110c', hairStyle: 'sidepart', eye: '#2f1b0f',
      facialHair: 'stubble', beard: '#1a110c', lip: '#9d625a', wrinkles: 0.3,
      outfit: { kind: 'blazer', color: '#3b3f4a', inner: '#ffffff' }, build: 'broad', blush: '#c47a62'
    })
  },
  {
    id: 'real-f-adult', name: 'Bopha', style: 'real', gender: 'female', age: 'adult',
    look: look({
      skinBase: '#93603f', hair: '#1a100c', hairHi: '#5a3e30', brow: '#1a100c', hairStyle: 'wavy', eye: '#241208',
      lip: '#a8404f', lashes: true, earrings: true, wrinkles: 0.15,
      outfit: { kind: 'blazer', color: '#1f6f6a', inner: '#f6efe6' }, build: 'slim', blush: '#b4605a',
      necklace: '#e7c76a'
    })
  },
  {
    id: 'real-m-old', name: 'Lok Sen', style: 'real', gender: 'male', age: 'old',
    look: look({
      skinBase: '#c99a70', ...WHITE, hairStyle: 'balding', eye: '#3a2a1a', facialHair: 'beard', lip: '#a8706a',
      wrinkles: 1, glasses: { color: '#3d3a38', shape: 'square' },
      outfit: { kind: 'cardigan', color: '#56624a', inner: '#f3efe4' }, build: 'regular', blush: '#c98a76'
    })
  },
  {
    id: 'real-f-old', name: 'Daun Pen', style: 'real', gender: 'female', age: 'old',
    look: look({
      skinBase: '#e0b78f', ...WHITE, hairStyle: 'bob', eye: '#4a3322', lip: '#bf6672', wrinkles: 1,
      necklace: '#f4efe6', earrings: true,
      outfit: { kind: 'cardigan', color: '#6d5a8c', inner: '#f6f1ea' }, build: 'slim', blush: '#e49a94'
    })
  }
];

const BY_ID = new Map(BUILTIN_AVATARS.map((a) => [a.id, a]));

/** The spec for an id; unknown ids fall back to the original host. */
export const avatarSpec = (id: string | null | undefined): AvatarSpec =>
  (id ? BY_ID.get(id) : undefined) ?? (BY_ID.get(DEFAULT_AVATAR_ID) as AvatarSpec);

export const isBuiltinAvatar = (id: string | null | undefined): boolean => !!id && BY_ID.has(id);
