/**
 * The rendering contract between backend and renderer.
 *
 * WHAT: a zod schema for the "composition payload" — a self-contained JSON
 *       description of one video (size, fps, scenes, media URLs, captions).
 * WHY:  the renderer must never query the database. The backend worker builds
 *       this payload, hands it over, and the renderer is a pure function of it.
 *       Zod validates the payload so a malformed job fails immediately with a
 *       clear message instead of producing a broken MP4.
 */
import { z } from 'zod';

export const captionSchema = z.object({
  text: z.string(),
  start: z.number().nonnegative(),
  end: z.number().nonnegative()
});

/** One spoken unit (an English word, a Khmer phrase) and when it is heard. */
export const wordSchema = z.object({
  text: z.string(),
  start: z.number().nonnegative(),
  end: z.number().nonnegative()
});

/** A text or sticker overlay the editor placed on a scene. Times are scene-relative seconds. */
export const layerSchema = z.object({
  id: z.string(),
  type: z.enum(['text', 'sticker']).default('text'),
  text: z.string(),
  /** Centre of the layer, % of frame width and height. */
  x: z.number().min(0).max(100).default(50),
  y: z.number().min(0).max(100).default(50),
  /** % of the frame's short side, so it scales with any resolution. */
  fontSize: z.number().positive().default(6),
  rotation: z.number().default(0),
  color: z.string().default('#ffffff'),
  background: z.string().nullable().default(null),
  weight: z.number().default(800),
  animation: z.enum(['none', 'pop', 'fade', 'slide_up', 'bounce']).default('pop'),
  start: z.number().nonnegative().default(0),
  end: z.number().positive().default(3)
});

export const sceneSchema = z.object({
  id: z.string(),
  sceneNumber: z.number().int().positive(),
  /** Seconds. The renderer converts to frames using project.fps. */
  duration: z.number().positive(),
  /** Absolute URL (MinIO/S3 presigned) or null to fall back to a solid colour. */
  visualUrl: z.string().nullable().default(null),
  /** Determines whether Remotion decodes visualUrl as a still image or video. */
  visualType: z.enum(['image', 'video']).nullable().default(null),
  audioUrl: z.string().nullable().default(null),
  onScreenText: z.string().nullable().default(null),
  narration: z.string().default(''),
  captions: z.array(captionSchema).default([]),
  transition: z.enum(['none', 'fade', 'slide']).default('fade'),
  backgroundColor: z.string().default('#0b0d12'),
  /** Speech marks from the TTS provider; drive karaoke captions. Empty => estimated. */
  words: z.array(wordSchema).default([]),
  /** Voice loudness per frame, 0-100, sampled at mouthFps; drives lip-sync. */
  mouth: z.array(z.number()).default([]),
  mouthFps: z.number().int().positive().default(30),
  /** The story's emotional beat for this scene; null => derived from position. */
  mood: z.enum(['hook', 'setup', 'rising', 'twist', 'climax', 'payoff']).nullable().default(null),
  /** Text and sticker overlays. */
  layers: z.array(layerSchema).default([]),
  /** Where in the narration audio this scene starts (after a split or trim), seconds. */
  audioStart: z.number().nonnegative().default(0),
  /** Narration volume 0..1. */
  voiceVolume: z.number().min(0).max(1).default(1),
  /** Volume of an uploaded clip's own sound 0..1 (0 = muted). */
  clipVolume: z.number().min(0).max(1).default(0),
  /** Where in the uploaded clip this scene starts, seconds. */
  trimStart: z.number().nonnegative().default(0),
  /** 'cover' fills the frame; 'contain' shows the whole picture. */
  mediaFit: z.enum(['cover', 'contain']).default('cover'),
  /** Slow zoom on still pictures. */
  kenBurns: z.boolean().default(true)
});

/**
 * Which host appears. 'builtin' picks one of the avatars in avatars.ts by id (unknown ids
 * fall back to the original cartoon host); 'photo' shows the user's uploaded picture.
 * mode (photo only): 'mouth' draws an animated mouth over the face, 'subtle' only breathes
 * and pulses with the voice.
 */
export const avatarSchema = z.object({
  kind: z.enum(['builtin', 'photo']).default('builtin'),
  id: z.string().default('toon-m-young'),
  imageUrl: z.string().nullable().default(null),
  mode: z.enum(['mouth', 'subtle']).default('mouth')
});

export const projectSchema = z.object({
  width: z.number().int().positive().default(1920),
  height: z.number().int().positive().default(1080),
  fps: z.number().int().positive().default(30),
  title: z.string().default('Untitled'),
  /** BCP-47-ish language tag. 'km' switches captions to the Khmer font stack. */
  language: z.string().default('en'),
  /** Background music bed, ducked under the narration. */
  music: z.boolean().default(true),
  /** Closing call to action at the end of the last scene. */
  cta: z.boolean().default(true),
  /** What the video is for; sets the badge in the corner. */
  purpose: z.enum(['story', 'product_demo', 'social_post', 'creator', 'explainer']).default('story'),
  /** Whether the animated host appears. Off: the scene's picture fills the frame. */
  presenter: z.boolean().default(true),
  /** Label of the closing call-to-action button; null keeps "Follow". */
  ctaText: z.string().nullable().default(null),
  /** The user's music track; null plays the built-in bed. Ignored when `music` is false. */
  musicUrl: z.string().nullable().default(null),
  /** Multiplier on the tuned music loudness, 0..1. */
  musicVolume: z.number().min(0).max(1).default(1),
  musicFadeIn: z.number().min(0).default(0.4),
  musicFadeOut: z.number().min(0).default(1),
  /** Lower the music while someone speaks. */
  musicDuck: z.boolean().default(true),
  /** The host. */
  avatar: avatarSchema.default({ kind: 'builtin', id: 'toon-m-young', imageUrl: null, mode: 'mouth' })
});

export const compositionSchema = z.object({
  project: projectSchema,
  scenes: z.array(sceneSchema).min(1)
}).refine(
  (payload) => payload.scenes.reduce((total, scene) => total + scene.duration, 0) <= 300,
  { message: 'Videos can be at most 5 minutes long.', path: ['scenes'] }
);

/**
 * One still image: the cover that represents a video in the project list and on
 * platforms. Same look as the video (backdrop, host, sticker), different text.
 */
export const thumbnailSchema = z.object({
  project: projectSchema,
  /** The big sticker text: what this particular video is about. */
  headline: z.string().min(1),
  /** Small label in the corner, e.g. "PRODUCT DEMO". */
  kicker: z.string().default(''),
  /** A scene picture to put behind everything; null draws the animated stage. */
  imageUrl: z.string().nullable().default(null),
  mood: z.enum(['hook', 'setup', 'rising', 'twist', 'climax', 'payoff']).default('hook'),
  /** Optional button-like chip at the bottom, e.g. "Try it today". */
  cta: z.string().nullable().default(null),
  /** Play the host and the backdrop instead of one settled frame (used for hover previews). */
  animate: z.boolean().default(false)
});

export type AvatarPayload = z.infer<typeof avatarSchema>;
export type Caption = z.infer<typeof captionSchema>;
export type Word = z.infer<typeof wordSchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type Layer = z.infer<typeof layerSchema>;
export type Project = z.infer<typeof projectSchema>;
export type CompositionPayload = z.infer<typeof compositionSchema>;
export type ThumbnailPayload = z.infer<typeof thumbnailSchema>;

export const emptyComposition: CompositionPayload = {
  project: {
    width: 1080,
    height: 1920,
    fps: 30,
    title: 'មេរៀនថ្មី',
    language: 'km',
    music: true,
    cta: true,
    purpose: 'story',
    presenter: true,
    ctaText: null,
    musicUrl: null,
    musicVolume: 1,
    musicFadeIn: 0.4,
    musicFadeOut: 1,
    musicDuck: true,
    avatar: { kind: 'builtin', id: 'toon-m-young', imageUrl: null, mode: 'mouth' }
  },
  scenes: [
    {
      id: 'placeholder',
      sceneNumber: 1,
      duration: 3,
      visualUrl: null,
      visualType: null,
      audioUrl: null,
      onScreenText: 'ចំណុចសំខាន់',
      narration: 'មេរៀនច្បាស់លាស់ ដែលពន្យល់ម្តងមួយគំនិត។',
      captions: [],
      transition: 'fade',
      backgroundColor: '#0b0d12',
      words: [],
      mouth: [],
      mouthFps: 30,
      mood: null,
      layers: [],
      audioStart: 0,
      voiceVolume: 1,
      clipVolume: 0,
      trimStart: 0,
      mediaFit: 'cover',
      kenBurns: true
    }
  ]
};

export const emptyThumbnail: ThumbnailPayload = {
  project: emptyComposition.project,
  headline: 'Your video',
  kicker: 'SORYA',
  imageUrl: null,
  mood: 'hook',
  cta: null,
  animate: false
};
