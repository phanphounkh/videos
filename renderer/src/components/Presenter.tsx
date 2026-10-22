/**
 * The animated storyteller who hosts every video.
 *
 * Everything is a pure function of the frame: the mouth follows the measured
 * voice loudness, the head nods on stressed syllables, the eyes blink and look
 * at the key-point sticker when it lands, and the arms gesture according to
 * the story beat. No randomness at render time, so every render is identical.
 */
import React, { useId } from 'react';
import { interpolate, spring } from 'remotion';
import type { PhaseTheme, StoryPhase } from '../story';

type Props = {
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
};

type Emotion = { brow: number; browTilt: number; smile: number; eyes: number; mouthBias: number };

const EMOTION: Record<StoryPhase, Emotion> = {
  hook: { brow: 12, browTilt: 0, smile: 1, eyes: 1.12, mouthBias: 0.1 },
  setup: { brow: 4, browTilt: 0, smile: 0.75, eyes: 1, mouthBias: 0 },
  rising: { brow: 7, browTilt: 7, smile: 0.5, eyes: 1.04, mouthBias: 0 },
  twist: { brow: 18, browTilt: 0, smile: 0.05, eyes: 1.28, mouthBias: 0.3 },
  climax: { brow: -5, browTilt: -10, smile: 0.35, eyes: 1.06, mouthBias: 0.05 },
  payoff: { brow: 8, browTilt: 0, smile: 1.2, eyes: 0.96, mouthBias: 0 }
};

/** Arm pose: shoulder angle from straight down (outward positive) and elbow bend. */
type Pose = { a: number; b: number; point?: boolean };

const SHOULDER_L = { x: 168, y: 566 };
const SHOULDER_R = { x: 432, y: 566 };
const UPPER = 118;
const FORE = 108;
const SKIN = '#f6c79a';
const SKIN_LIGHT = '#ffe3c4';
const SKIN_LINE = '#c98a5c';
const HAIR = '#24160f';

const mix = (from: Pose, to: Pose, t: number): Pose => ({
  a: from.a + (to.a - from.a) * t,
  b: from.b + (to.b - from.b) * t,
  point: t > 0.5 ? to.point : from.point
});

/** Gesture loop for each story beat, animated by time and voice. */
const phasePose = (phase: StoryPhase, side: 'L' | 'R', t: number, loud: number): Pose => {
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

const Arm: React.FC<{ side: 'L' | 'R'; pose: Pose; shirt: string; shade: string }> = ({ side, pose, shirt, shade }) => {
  const sign = side === 'L' ? -1 : 1;
  const shoulder = side === 'L' ? SHOULDER_L : SHOULDER_R;
  const rad = (deg: number) => (deg * Math.PI) / 180;
  const elbow = {
    x: shoulder.x + sign * Math.sin(rad(pose.a)) * UPPER,
    y: shoulder.y + Math.cos(rad(pose.a)) * UPPER
  };
  const foreAngle = pose.a + pose.b;
  const dir = { x: sign * Math.sin(rad(foreAngle)), y: Math.cos(rad(foreAngle)) };
  const hand = { x: elbow.x + dir.x * FORE, y: elbow.y + dir.y * FORE };
  const tip = { x: hand.x + dir.x * 40, y: hand.y + dir.y * 40 };

  return (
    <g>
      <path
        d={`M${shoulder.x} ${shoulder.y} L${elbow.x} ${elbow.y}`}
        stroke={shade}
        strokeWidth={60}
        strokeLinecap="round"
      />
      <path
        d={`M${shoulder.x} ${shoulder.y} L${elbow.x} ${elbow.y}`}
        stroke={shirt}
        strokeWidth={50}
        strokeLinecap="round"
      />
      <path d={`M${elbow.x} ${elbow.y} L${hand.x} ${hand.y}`} stroke={SKIN_LINE} strokeWidth={42} strokeLinecap="round" />
      <path d={`M${elbow.x} ${elbow.y} L${hand.x} ${hand.y}`} stroke={SKIN} strokeWidth={34} strokeLinecap="round" />
      {pose.point ? (
        <>
          <path d={`M${hand.x} ${hand.y} L${tip.x} ${tip.y}`} stroke={SKIN_LINE} strokeWidth={20} strokeLinecap="round" />
          <path d={`M${hand.x} ${hand.y} L${tip.x} ${tip.y}`} stroke={SKIN} strokeWidth={13} strokeLinecap="round" />
        </>
      ) : null}
      <circle cx={hand.x} cy={hand.y} r={29} fill={SKIN} stroke={SKIN_LINE} strokeWidth={5} />
    </g>
  );
};

/** Blink pattern: irregular but deterministic, never during the first frames. */
const eyelid = (frame: number, fps: number): number => {
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

export const Presenter: React.FC<Props> = ({
  frame,
  fps,
  mouthOpen,
  loudness,
  talking,
  phase,
  theme,
  cueFrame,
  cueSide,
  celebrateFrom
}) => {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '');
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

  // Mouth geometry: corners lift with the smile; an open mouth narrows to an "O".
  const mx = 300;
  const cornerY = 402 - smile * 7;
  const width = 78 + smile * 14 - open * 18;
  const depth = 3 + open * 46;
  const curve = smile * 16;
  const mouthPath = `M${mx - width / 2} ${cornerY} Q${mx} ${cornerY - 4 - open * 8} ${mx + width / 2} ${cornerY} Q${mx} ${cornerY + curve + depth * 2} ${mx - width / 2} ${cornerY} Z`;

  const shirt = `url(#shirt-${uid})`;

  return (
    <svg viewBox="0 0 600 760" width="100%" height="100%" aria-label="Storyteller" style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={`shirt-${uid}`} x1="0" y1="0" x2="0.4" y2="1">
          <stop offset="0" stopColor={theme.glow} />
          <stop offset="1" stopColor={theme.shade} />
        </linearGradient>
        <radialGradient id={`skin-${uid}`} cx="0.42" cy="0.35" r="0.75">
          <stop offset="0" stopColor={SKIN_LIGHT} />
          <stop offset="1" stopColor={SKIN} />
        </radialGradient>
        <clipPath id={`mouth-${uid}`}>
          <path d={mouthPath} />
        </clipPath>
      </defs>

      <g transform={`translate(300 760) scale(${1 / squash} ${squash}) translate(-300 -760) translate(0 ${breath * 0.5})`}>
        {/* Body */}
        <rect x="266" y="440" width="68" height="100" rx="30" fill={SKIN} />
        <path d="M100 780 C104 618 168 528 300 522 C432 528 496 618 500 780 Z" fill={shirt} />
        <path d="M244 526 Q300 600 356 526" fill="none" stroke="#ffffff" strokeOpacity="0.9" strokeWidth="12" strokeLinecap="round" />
        <path d="M300 590 L300 760" stroke="#000000" strokeOpacity="0.12" strokeWidth="6" />

        <Arm side="L" pose={left} shirt={shirt} shade={theme.shade} />
        <Arm side="R" pose={right} shirt={shirt} shade={theme.shade} />

        {/* Head */}
        <g transform={`translate(0 ${breath + nod}) rotate(${tilt} 300 430)`}>
          <circle cx="152" cy="318" r="30" fill={SKIN} stroke={SKIN_LINE} strokeWidth="5" />
          <circle cx="448" cy="318" r="30" fill={SKIN} stroke={SKIN_LINE} strokeWidth="5" />
          <ellipse cx="300" cy="300" rx="150" ry="158" fill={`url(#skin-${uid})`} stroke={SKIN_LINE} strokeWidth="6" />

          {/* Hair, with a cowlick that bounces with the voice. */}
          <path
            d="M152 300 C140 168 230 118 312 124 C402 130 462 188 448 300 C432 236 398 206 352 198 C318 226 248 230 196 214 C176 236 160 262 152 300 Z"
            fill={HAIR}
          />
          <path
            d={`M298 128 C292 ${92 - loudness * 10} ${318 + Math.sin(t * 4) * 6} ${70 - loudness * 12} ${344 + Math.sin(t * 4) * 8} ${84 - loudness * 8}`}
            fill="none"
            stroke={HAIR}
            strokeWidth="16"
            strokeLinecap="round"
          />

          {/* Brows */}
          <path
            d="M208 248 Q242 230 276 246"
            fill="none"
            stroke={HAIR}
            strokeWidth="13"
            strokeLinecap="round"
            transform={`translate(0 ${-browLift}) rotate(${emotion.browTilt} 242 244)`}
          />
          <path
            d="M324 246 Q358 230 392 248"
            fill="none"
            stroke={HAIR}
            strokeWidth="13"
            strokeLinecap="round"
            transform={`translate(0 ${-browLift - (phase === 'rising' ? 8 : 0)}) rotate(${-emotion.browTilt} 358 244)`}
          />

          {/* Eyes */}
          {[242, 358].map((cx) => (
            <g key={cx} transform={`translate(${cx} 304) scale(1 ${Math.max(0.06, eyeScale)}) translate(${-cx} -304)`}>
              <ellipse cx={cx} cy="304" rx="31" ry="35" fill="#ffffff" stroke={SKIN_LINE} strokeWidth="4" />
              <circle cx={cx + gaze.x} cy={304 + gaze.y} r="20" fill="#4a2a18" />
              <circle cx={cx + gaze.x} cy={304 + gaze.y} r="11" fill="#0b0b0b" />
              <circle cx={cx + gaze.x - 7} cy={304 + gaze.y - 8} r="6.5" fill="#ffffff" />
              <circle cx={cx + gaze.x + 6} cy={304 + gaze.y + 7} r="3" fill="#ffffff" opacity="0.8" />
            </g>
          ))}

          {/* Nose and cheeks */}
          <path d="M292 352 Q300 362 310 352" fill="none" stroke={SKIN_LINE} strokeWidth="6" strokeLinecap="round" />
          <ellipse cx="200" cy="372" rx="26" ry="15" fill="#fb7185" opacity={0.28 + smile * 0.08} />
          <ellipse cx="400" cy="372" rx="26" ry="15" fill="#fb7185" opacity={0.28 + smile * 0.08} />

          {/* Mouth: interior, teeth and tongue clipped to the lip shape. */}
          <path d={mouthPath} fill="#5b1226" />
          <g clipPath={`url(#mouth-${uid})`}>
            <rect x={mx - 60} y={cornerY - 30} width="120" height={36 + depth * 0.15} rx="8" fill="#ffffff" />
            <ellipse cx={mx} cy={cornerY + curve * 0.5 + depth * 1.05} rx={width * 0.34} ry={8 + depth * 0.3} fill="#f472b6" />
          </g>
          <path d={mouthPath} fill="none" stroke="#3b0a17" strokeWidth="5" strokeLinejoin="round" />
        </g>
      </g>
    </svg>
  );
};
