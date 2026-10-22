/**
 * Shared timing and look decisions.
 *
 * WHY one module: the scene draws the sticker, the camera punch and the CTA,
 * while the composition schedules the matching sound effects. Both read their
 * timing from here, so a "pop" can never drift away from the sticker it belongs to.
 */
import type { Scene } from './schema';

export type StoryPhase = 'hook' | 'setup' | 'rising' | 'twist' | 'climax' | 'payoff';

export type PhaseTheme = {
  /** Deep background base. */
  base: string;
  /** Saturated light colour for glows and the presenter's shirt. */
  glow: string;
  /** Bright accent for stickers, karaoke highlight and progress bar. */
  accent: string;
  /** Shirt gradient end. */
  shade: string;
};

export const PHASE_THEME: Record<StoryPhase, PhaseTheme> = {
  hook: { base: '#2a0b12', glow: '#f97316', accent: '#ffd23f', shade: '#9a3412' },
  setup: { base: '#0c1631', glow: '#3b82f6', accent: '#7dd3fc', shade: '#1e3a8a' },
  rising: { base: '#04282a', glow: '#14b8a6', accent: '#5eead4', shade: '#115e59' },
  twist: { base: '#25094f', glow: '#a855f7', accent: '#f0abfc', shade: '#581c87' },
  climax: { base: '#360808', glow: '#ef4444', accent: '#fde047', shade: '#991b1b' },
  payoff: { base: '#2f1a05', glow: '#f59e0b', accent: '#fde68a', shade: '#92400e' }
};

export const getStoryPhase = (sceneNumber: number, sceneCount: number): StoryPhase => {
  if (sceneNumber <= 1) return 'hook';
  const progress = (sceneNumber - 1) / Math.max(1, sceneCount - 1);
  if (progress < 0.28) return 'setup';
  if (progress < 0.58) return 'rising';
  if (progress < 0.76) return 'twist';
  if (progress < 0.92) return 'climax';
  return 'payoff';
};

/** The scene's beat: what the story says it is, else where it sits in the video. */
export const sceneMood = (scene: Scene, sceneCount: number): StoryPhase =>
  scene.mood ?? getStoryPhase(scene.sceneNumber, sceneCount);

export const fontFor = (language: string): string =>
  language.startsWith('km')
    ? "'Noto Sans Khmer', 'Khmer OS Battambang', 'Khmer OS', sans-serif"
    : "'Inter', 'Noto Sans', system-ui, sans-serif";

/** Frames the entry transition takes; the whoosh is centred on it. */
export const TRANSITION_FRAMES = 10;

/** When the scene's key-point sticker is on screen, in scene-relative frames. */
export const stickerWindow = (
  scene: Scene,
  fps: number,
  durationInFrames: number
): { start: number; end: number } | null => {
  if (!scene.onScreenText) return null;
  // The hook must grab attention in the first second, so its sticker lands
  // almost immediately; later scenes let the presenter start talking first.
  const start = Math.min(
    Math.round((scene.sceneNumber === 1 ? 0.15 : 0.55) * fps),
    Math.round(durationInFrames * 0.2)
  );
  const end = Math.max(start + 12, Math.min(durationInFrames - Math.round(0.2 * fps), start + Math.round(5.5 * fps)));
  return { start, end };
};

/** When the closing "Follow" call to action shows, in scene-relative frames. */
export const ctaWindow = (fps: number, durationInFrames: number): { start: number; end: number } => {
  const length = Math.min(Math.round(2.8 * fps), Math.round(durationInFrames * 0.6));
  return { start: durationInFrames - length, end: durationInFrames };
};

/** Voice loudness 0..1 at a scene-relative frame, with a short release so the mouth eases shut. */
export const loudnessAt = (scene: Scene, frame: number, fps: number): number => {
  if (scene.mouth.length === 0) return 0;
  const sample = (f: number): number => {
    const index = Math.floor((f / fps) * scene.mouthFps);
    return index >= 0 && index < scene.mouth.length ? scene.mouth[index] / 100 : 0;
  };
  return Math.max(sample(frame), sample(frame - 1) * 0.7, sample(frame - 2) * 0.4);
};

/** Seconds (scene-relative) between which the narration is actually heard. */
export const speechSpan = (scene: Scene): { start: number; end: number } | null => {
  if (!scene.audioUrl) return null;
  if (scene.words.length > 0) {
    return { start: scene.words[0].start, end: scene.words[scene.words.length - 1].end };
  }
  return { start: 0.1, end: Math.max(0.2, scene.duration - 0.35) };
};

/**
 * How open the presenter's mouth is, 0..1.
 *
 * Uses the measured loudness when the backend supplied it. Older scenes only
 * have an audio file, so they get a plausible talking rhythm while speech is
 * expected; silent scenes keep the mouth shut instead of miming.
 */
export const mouthOpenAt = (scene: Scene, frame: number, fps: number): number => {
  if (scene.mouth.length > 0) {
    const loud = loudnessAt(scene, frame, fps);
    return Math.min(1, Math.max(0, (loud - 0.1) / 0.75));
  }
  const span = speechSpan(scene);
  const t = frame / fps;
  if (!span || t < span.start || t > span.end) return 0;
  const syllable = Math.abs(Math.sin(frame * 0.55)) * (0.55 + 0.45 * Math.abs(Math.sin(frame * 0.13)));
  return syllable;
};
