/**
 * The animation brain shared by every host (cartoon, realistic, photo).
 *
 * Everything is a pure function of the frame: the mouth follows the measured voice
 * loudness, the head nods on stressed syllables, the eyes blink and look at the key-point
 * sticker when it lands, and the arms gesture according to the story beat. No randomness
 * at render time, so every render is identical.
 */
import { interpolate, spring } from 'remotion';
import type { PhaseTheme, StoryPhase } from '../story';

export type HostProps = {
  frame: number;
  fps: number;
  /** Mouth openness 0..1 for this frame. */
  mouthOpen: number;
  /** Voice loudness 0..1 for this frame (drives nods and gestures). */
  loudness: number;
  /** Whether the narration is being heard right now. */
  talking: boolean;
  phase: StoryPhase;
  theme: PhaseTheme;
  /** Frame the key-point sticker lands, if any: the presenter points and looks at it. */
  cueFrame: number | null;
  /** Where the sticker is relative to the presenter. */
  cueSide: 'up' | 'left' | 'right';
  /** Wave and grin for the closing call to action. */
  celebrateFrom: number | null;
  /** Override the SVG viewBox (used for bust crops of the avatar previews). */
  viewBox?: string;
};

export type Emotion = { brow: number; browTilt: number; smile: number; eyes: number; mouthBias: number };

export const EMOTION: Record<StoryPhase, Emotion> = {
  hook: { brow: 12, browTilt: 0, smile: 1, eyes: 1.12, mouthBias: 0.1 },
  setup: { brow: 4, browTilt: 0, smile: 0.75, eyes: 1, mouthBias: 0 },
  rising: { brow: 7, browTilt: 7, smile: 0.5, eyes: 1.04, mouthBias: 0 },
  twist: { brow: 18, browTilt: 0, smile: 0.05, eyes: 1.28, mouthBias: 0.3 },
  climax: { brow: -5, browTilt: -10, smile: 0.35, eyes: 1.06, mouthBias: 0.05 },
  payoff: { brow: 8, browTilt: 0, smile: 1.2, eyes: 0.96, mouthBias: 0 }
};

/** Arm pose: shoulder angle from straight down (outward positive) and elbow bend. */
export type Pose = { a: number; b: number; point?: boolean };

export const mix = (from: Pose, to: Pose, t: number): Pose => ({
  a: from.a + (to.a - from.a) * t,
  b: from.b + (to.b - from.b) * t,
  point: t > 0.5 ? to.point : from.point
});

/** Gesture loop for each story beat, animated by time and voice. */
export const phasePose = (phase: StoryPhase, side: 'L' | 'R', t: number, loud: number): Pose => {
  const sway = Math.sin(t * 1.7 + (side === 'L' ? 0 : 1.9));
  const beat = Math.sin(t * 3.1 + (side === 'L' ? 0.6 : 0));
  switch (phase) {
    case 'hook':
      return side === 'R'
        ? { a: 142 + Math.sin(t * 9) * 14, b: 28 + Math.sin(t * 9 + 0.8) * 22 }
        : { a: 34 + sway * 6 + loud * 10, b: 96 + beat * 14 };
    case 'twist':
      return { a: 58 + beat * 5, b: 118 + sway * 8 + loud * 6 };
    case 'climax':
      return side === 'R'
        ? { a: 150 + Math.abs(Math.sin(t * 5)) * 14, b: -24 }
        : { a: 30 + loud * 14, b: -112 + beat * 10 };
    case 'payoff':
      return side === 'R'
        ? { a: 128 + Math.sin(t * 8) * 12, b: 34 + Math.sin(t * 8 + 0.8) * 18 }
        : { a: 26 + loud * 10, b: 88 + beat * 12 };
    case 'rising':
      return side === 'L'
        ? { a: 26 + loud * 12, b: -118 + beat * 12 }
        : { a: 38 + sway * 8 + loud * 10, b: 92 + beat * 18 };
    default:
      return { a: 30 + sway * 8 + loud * 14, b: 84 + beat * 22 + loud * 10 };
  }
};

/** Blink pattern: irregular but deterministic, never during the first frames. */
export const eyelid = (frame: number, fps: number): number => {
  const cycle = Math.round(3.4 * fps);
  const offsets = [0, Math.round(1.1 * fps), Math.round(2.6 * fps)];
  const local = frame % (cycle * 3);
  const blinkAt = [cycle - 7, cycle * 2 - 7 - offsets[1] % 9, cycle * 3 - 7 - offsets[2] % 13];
  // A double blink every third cycle reads as natural rather than robotic.
  const starts = [...blinkAt, blinkAt[2] - 9];
  for (const start of starts) {
    const k = local - start;
    if (k >= 0 && k < 6) return 1 - Math.sin((Math.PI * k) / 6);
  }
  return 1;
};

export const useHostMotion = (props: HostProps) => {
  const { frame, fps, mouthOpen, loudness, talking, phase, cueFrame, cueSide, celebrateFrom } = props;
  const t = frame / fps;
  const emotion = EMOTION[phase];
  const celebrating = celebrateFrom !== null && frame >= celebrateFrom;

  // Landing hop at the start of each scene: a little squash and stretch.
  const hop = spring({ frame, fps, config: { damping: 9, stiffness: 160, mass: 0.6 } });
  const squash = 1 + (1 - hop) * 0.08;

  // Head: breathing bob, slow tilt, and a nod on each stressed syllable.
  const breath = Math.sin(t * 2.1) * 4;
  const nod = talking ? loudness * 9 : 0;
  const tilt = Math.sin(t * 0.9) * 3 + (talking ? Math.sin(t * 6.3) * loudness * 3 : 0) + (phase === 'rising' ? 4 : 0);

  // React to the sticker: point and look at it, then ease back.
  const cueAge = cueFrame === null ? -1 : frame - cueFrame;
  const cue = cueAge < 0
    ? 0
    : interpolate(cueAge, [0, 6, Math.round(1.1 * fps), Math.round(1.5 * fps)], [0, 1, 1, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp'
      });

  const pointPose: Pose = cueSide === 'up' ? { a: 154, b: 8, point: true } : { a: 96, b: -4, point: true };
  const pointArm: 'L' | 'R' = cueSide === 'left' ? 'L' : 'R';
  let left = phasePose(phase, 'L', t, talking ? loudness : 0);
  let right = phasePose(phase, 'R', t, talking ? loudness : 0);
  if (pointArm === 'L') left = mix(left, pointPose, cue);
  else right = mix(right, pointPose, cue);
  if (celebrating) {
    const c = spring({ frame: frame - (celebrateFrom ?? 0), fps, config: { damping: 12 } });
    // Both hands wave goodbye while the viewer is asked to follow.
    right = mix(right, { a: 140 + Math.sin(t * 9) * 14, b: 28 + Math.sin(t * 9 + 0.8) * 20 }, c);
    left = mix(left, { a: 140 + Math.sin(t * 9 + 1.6) * 14, b: 28 + Math.sin(t * 9 + 2.4) * 20 }, c);
  }

  const gaze = {
    x: (cueSide === 'left' ? -9 : cueSide === 'right' ? 9 : 0) * cue + Math.sin(t * 0.7) * 2,
    y: (cueSide === 'up' ? -9 : -3) * cue + Math.sin(t * 0.5) * 1.5
  };
  const lid = Math.min(eyelid(frame, fps), celebrating ? 0.85 : 1);
  const eyeScale = emotion.eyes * lid;
  const browLift = emotion.brow + (talking ? loudness * 6 : 0) + cue * 6;
  const smile = celebrating ? 1.3 : emotion.smile;
  const open = Math.min(1, mouthOpen + (mouthOpen > 0.05 ? emotion.mouthBias * 0.5 : 0));

  return {
    t, emotion, celebrating, squash, breath, nod, tilt, cue, left, right, gaze, lid, eyeScale, browLift, smile, open
  };
};
