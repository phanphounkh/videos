/**
 * The animated cartoon storyteller who hosts videos ("toon" avatars).
 *
 * Animation logic lives in hostMotion.ts (shared with the realistic and photo hosts);
 * this file draws the cartoon. The drawing is driven by an AvatarLook: with the default
 * look (toon-m-young, the original host) the output is identical to the very first
 * version of this component, so existing videos never change.
 */
import React, { useId } from 'react';
import { avatarSpec, mixHex, type AvatarLook } from '../avatars';
import { useHostMotion, type HostProps, type Pose } from './hostMotion';

type Props = HostProps & {
  /** The cartoon look; defaults to the original host. */
  look?: AvatarLook;
};

const UPPER = 118;
const FORE = 108;

const SHOULDERS: Record<AvatarLook['build'], { l: { x: number; y: number }; r: { x: number; y: number }; body: string; neck: [number, number] }> = {
  slim: {
    l: { x: 176, y: 566 },
    r: { x: 424, y: 566 },
    body: 'M118 780 C120 622 178 530 300 524 C422 530 480 622 482 780 Z',
    neck: [274, 52]
  },
  regular: {
    l: { x: 168, y: 566 },
    r: { x: 432, y: 566 },
    body: 'M100 780 C104 618 168 528 300 522 C432 528 496 618 500 780 Z',
    neck: [266, 68]
  },
  broad: {
    l: { x: 156, y: 566 },
    r: { x: 444, y: 566 },
    body: 'M80 780 C86 612 158 526 300 520 C442 526 514 612 520 780 Z',
    neck: [262, 76]
  }
};

const Arm: React.FC<{
  side: 'L' | 'R';
  pose: Pose;
  shirt: string;
  shade: string;
  shoulder: { x: number; y: number };
  skin: string;
  skinLine: string;
}> = ({ side, pose, shirt, shade, shoulder, skin, skinLine }) => {
  const sign = side === 'L' ? -1 : 1;
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
      <path d={`M${shoulder.x} ${shoulder.y} L${elbow.x} ${elbow.y}`} stroke={shade} strokeWidth={60} strokeLinecap="round" />
      <path d={`M${shoulder.x} ${shoulder.y} L${elbow.x} ${elbow.y}`} stroke={shirt} strokeWidth={50} strokeLinecap="round" />
      <path d={`M${elbow.x} ${elbow.y} L${hand.x} ${hand.y}`} stroke={skinLine} strokeWidth={42} strokeLinecap="round" />
      <path d={`M${elbow.x} ${elbow.y} L${hand.x} ${hand.y}`} stroke={skin} strokeWidth={34} strokeLinecap="round" />
      {pose.point ? (
        <>
          <path d={`M${hand.x} ${hand.y} L${tip.x} ${tip.y}`} stroke={skinLine} strokeWidth={20} strokeLinecap="round" />
          <path d={`M${hand.x} ${hand.y} L${tip.x} ${tip.y}`} stroke={skin} strokeWidth={13} strokeLinecap="round" />
        </>
      ) : null}
      <circle cx={hand.x} cy={hand.y} r={29} fill={skin} stroke={skinLine} strokeWidth={5} />
    </g>
  );
};

/** Hair behind the head (long styles, bun, ponytail) and in front of it (fringe, cap). */
const hairLayers = (look: AvatarLook, t: number, loudness: number) => {
  const hair = look.hair;
  const hi = look.hairHi;
  const CAP_BASE =
    'M152 300 C140 168 230 118 312 124 C402 130 462 188 448 300 C432 236 398 206 352 198 C318 226 248 230 196 214 C176 236 160 262 152 300 Z';
  const BANGS =
    'M150 304 C138 168 228 114 300 116 C382 114 464 170 450 304 C442 262 424 232 396 214 C346 244 252 244 204 214 C176 238 158 266 150 304 Z';
  const swing = Math.sin(t * 2.6) * 5;
  switch (look.hairStyle) {
    case 'sidepart':
      return {
        back: null,
        front: (
          <>
            <path
              d="M150 304 C136 170 226 112 314 116 C410 122 468 190 450 304 C438 258 414 226 376 212 C316 244 228 238 190 262 C166 272 156 288 150 304 Z"
              fill={hair}
            />
            <path d="M244 124 Q268 160 232 214" fill="none" stroke={hi} strokeWidth="6" strokeLinecap="round" opacity="0.55" />
            <path d="M330 126 Q400 140 432 214" fill="none" stroke={hi} strokeWidth="5" strokeLinecap="round" opacity="0.35" />
          </>
        )
      };
    case 'balding':
      return {
        back: null,
        front: (
          <>
            <path d="M153 306 C140 262 152 214 184 188 C170 226 176 262 198 290 C194 306 182 320 164 326 Z" fill={hair} />
            <path d="M447 306 C460 262 448 214 416 188 C430 226 424 262 402 290 C406 306 418 320 436 326 Z" fill={hair} />
            <ellipse cx="250" cy="176" rx="38" ry="13" fill="#ffffff" opacity="0.22" transform="rotate(-18 250 176)" />
          </>
        )
      };
    case 'bob':
    case 'wavy':
      return {
        back: (
          <>
            <path
              d="M138 300 C116 148 220 98 300 100 C390 98 484 148 462 300 C468 384 472 440 452 480 C420 496 392 488 384 470 L216 470 C208 488 180 496 148 480 C128 440 132 384 138 300 Z"
              fill={hair}
            />
          </>
        ),
        front: (
          <>
            <path d={BANGS} fill={hair} />
            <path d="M150 296 C138 372 148 432 168 472 C192 480 212 466 220 450 C198 420 192 360 208 252 Z" fill={hair} />
            <path d="M450 296 C462 372 452 432 432 472 C408 480 388 466 380 450 C402 420 408 360 392 252 Z" fill={hair} />
            <path d="M230 138 Q262 124 300 128" fill="none" stroke={hi} strokeWidth="7" strokeLinecap="round" opacity="0.45" />
          </>
        )
      };
    case 'long':
      return {
        back: (
          <path
            d="M138 300 C116 150 220 100 300 102 C390 100 484 150 462 300 C470 420 482 540 470 640 C440 660 400 640 390 600 L210 600 C200 640 160 660 130 640 C118 540 130 420 138 300 Z"
            fill={hair}
          />
        ),
        front: (
          <>
            <path d={BANGS} fill={hair} />
            <path d="M150 296 C136 400 140 500 128 590 C160 600 192 560 204 500 C196 420 196 340 206 252 Z" fill={hair} />
            <path d="M450 296 C464 400 460 500 472 590 C440 600 408 560 396 500 C404 420 404 340 394 252 Z" fill={hair} />
          </>
        )
      };
    case 'ponytail':
      return {
        back: (
          <g transform={`rotate(${swing} 430 168)`}>
            <path d="M418 150 C488 118 540 192 528 292 C522 362 500 420 518 480 C480 458 462 386 462 304 C462 244 446 206 408 194 Z" fill={hair} />
            <path d="M486 172 C510 220 510 300 498 380" fill="none" stroke={hi} strokeWidth="6" strokeLinecap="round" opacity="0.4" />
          </g>
        ),
        front: (
          <>
            <path d={BANGS} fill={hair} />
            <circle cx="428" cy="170" r="15" fill="#f472b6" stroke="#be185d" strokeWidth="3" />
          </>
        )
      };
    case 'bun':
      return {
        back: (
          <>
            <circle cx="300" cy="104" r="52" fill={hair} />
            <path d="M262 92 Q300 66 338 92" fill="none" stroke={hi} strokeWidth="6" strokeLinecap="round" opacity="0.7" />
          </>
        ),
        front: (
          <>
            <path
              d="M150 304 C136 168 226 114 300 116 C380 114 466 170 450 304 C440 258 414 222 376 208 C330 192 270 192 224 208 C186 222 160 258 150 304 Z"
              fill={hair}
            />
            <path d="M300 118 L300 180" stroke={hi} strokeWidth="4" opacity="0.6" />
          </>
        )
      };
    case 'cropped':
    case 'short':
    default:
      return {
        back: null,
        front: (
          <>
            <path d={CAP_BASE} fill={hair} />
            {look.cowlick ? (
              <path
                d={`M298 128 C292 ${92 - loudness * 10} ${318 + Math.sin(t * 4) * 6} ${70 - loudness * 12} ${344 + Math.sin(t * 4) * 8} ${84 - loudness * 8}`}
                fill="none"
                stroke={hair}
                strokeWidth="16"
                strokeLinecap="round"
              />
            ) : null}
          </>
        )
      };
  }
};

export const Presenter: React.FC<Props> = (props) => {
  const { loudness, phase, theme, viewBox } = props;
  const look = props.look ?? avatarSpec('toon-m-young').look;
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '');
  const m = useHostMotion(props);
  const { t, emotion, squash, breath, nod, tilt, gaze, eyeScale, browLift, smile, open } = m;

  const SKIN = look.skin;
  const SKIN_LIGHT = look.skinLight;
  const SKIN_LINE = look.skinLine;
  const build = SHOULDERS[look.build];
  const k = look.eyeScale;
  const fw = 150 * look.faceWidth;
  const fh = 158 * look.faceLength;
  const wr = look.wrinkles;
  const outfit = look.outfit;
  const jacket = outfit.color;

  // Mouth geometry: corners lift with the smile; an open mouth narrows to an "O".
  const mx = 300;
  const cornerY = 402 - smile * 7;
  const width = 78 + smile * 14 - open * 18;
  const depth = 3 + open * 46;
  const curve = smile * 16;
  const mouthPath = `M${mx - width / 2} ${cornerY} Q${mx} ${cornerY - 4 - open * 8} ${mx + width / 2} ${cornerY} Q${mx} ${cornerY + curve + depth * 2} ${mx - width / 2} ${cornerY} Z`;

  const shirt = `url(#shirt-${uid})`;
  const shadeColor = jacket ? mixHex(jacket, '#000000', 0.35) : theme.shade;
  const hairParts = hairLayers(look, t, loudness);
  const browColor = look.brow;
  const lens = look.glasses;
  const leftArm = build.l;
  const rightArm = build.r;

  const eyeXs = [242, 358];

  return (
    <svg viewBox={viewBox ?? '0 0 600 760'} width="100%" height="100%" aria-label="Storyteller" style={{ overflow: 'visible' }}>
      <defs>
        <linearGradient id={`shirt-${uid}`} x1="0" y1="0" x2="0.4" y2="1">
          <stop offset="0" stopColor={jacket ? mixHex(jacket, '#ffffff', 0.18) : theme.glow} />
          <stop offset="1" stopColor={jacket ? mixHex(jacket, '#000000', 0.3) : theme.shade} />
        </linearGradient>
        <radialGradient id={`skin-${uid}`} cx="0.42" cy="0.35" r="0.75">
          <stop offset="0" stopColor={SKIN_LIGHT} />
          <stop offset="1" stopColor={SKIN} />
        </radialGradient>
        <clipPath id={`mouth-${uid}`}>
          <path d={mouthPath} />
        </clipPath>
        <clipPath id={`face-${uid}`}>
          <ellipse cx="300" cy="300" rx={fw} ry={fh} />
        </clipPath>
        {eyeXs.map((cx) => (
          <clipPath key={cx} id={`eye-${uid}-${cx}`}>
            <ellipse cx={cx} cy="304" rx={31 * k} ry={35 * k} />
          </clipPath>
        ))}
      </defs>

      <g transform={`translate(300 760) scale(${1 / squash} ${squash}) translate(-300 -760) translate(0 ${breath * 0.5})`}>
        {/* Body */}
        <rect x={build.neck[0]} y="440" width={build.neck[1]} height="100" rx="30" fill={SKIN} />
        <path d={build.body} fill={shirt} />
        {outfit.kind === 'tee' ? (
          <>
            <path d="M244 526 Q300 600 356 526" fill="none" stroke="#ffffff" strokeOpacity="0.9" strokeWidth="12" strokeLinecap="round" />
            <path d="M300 590 L300 760" stroke="#000000" strokeOpacity="0.12" strokeWidth="6" />
          </>
        ) : null}
        {outfit.kind === 'collar' ? (
          <>
            <path d="M262 524 L300 596 L338 524 Z" fill={SKIN} />
            <path d="M256 514 L300 600 L218 560 Z" fill={outfit.inner} stroke="#00000022" strokeWidth="2" />
            <path d="M344 514 L300 600 L382 560 Z" fill={outfit.inner} stroke="#00000022" strokeWidth="2" />
            <path d="M300 600 L300 760" stroke="#000000" strokeOpacity="0.14" strokeWidth="5" />
          </>
        ) : null}
        {outfit.kind === 'scoop' ? (
          <>
            <path d="M240 526 Q300 628 360 526 Z" fill={SKIN} />
            <path d="M240 526 Q300 628 360 526" fill="none" stroke={outfit.inner} strokeWidth="10" strokeLinecap="round" />
          </>
        ) : null}
        {outfit.kind === 'blazer' ? (
          <>
            <path d="M246 522 Q300 660 354 522 Z" fill={outfit.inner} />
            <path d="M272 524 L300 584 L328 524 Z" fill={SKIN} />
            <path d="M252 516 L296 668 L240 676 L204 566 Z" fill={shadeColor} stroke="#00000022" strokeWidth="2" />
            <path d="M348 516 L304 668 L360 676 L396 566 Z" fill={shadeColor} stroke="#00000022" strokeWidth="2" />
            <path d="M300 668 L300 770" stroke="#000000" strokeOpacity="0.2" strokeWidth="5" />
          </>
        ) : null}
        {outfit.kind === 'cardigan' || outfit.kind === 'blouse' ? (
          <>
            <path d="M242 524 Q300 616 358 524 Z" fill={outfit.inner} />
            <path d="M268 526 Q300 580 332 526 Z" fill={SKIN} />
            <path d="M262 530 L282 770 M338 530 L318 770" stroke={shadeColor} strokeWidth="10" strokeLinecap="round" opacity="0.7" />
            {[640, 690, 740].map((y) => (
              <circle key={y} cx={286} cy={y} r="6" fill={outfit.inner} stroke="#00000033" strokeWidth="2" />
            ))}
          </>
        ) : null}
        {look.necklace ? (
          <path
            d={outfit.kind === 'scoop' ? 'M252 540 Q300 630 348 540' : 'M256 536 Q300 604 344 536'}
            fill="none"
            stroke={look.necklace}
            strokeWidth="7"
            strokeLinecap="round"
            strokeDasharray="1 11"
          />
        ) : null}

        <Arm side="L" pose={m.left} shirt={shirt} shade={shadeColor} shoulder={leftArm} skin={SKIN} skinLine={SKIN_LINE} />
        <Arm side="R" pose={m.right} shirt={shirt} shade={shadeColor} shoulder={rightArm} skin={SKIN} skinLine={SKIN_LINE} />

        {/* Head */}
        <g transform={`translate(0 ${breath + nod}) rotate(${tilt} 300 430)`}>
          {hairParts.back}
          <circle cx={300 - fw + 2} cy="318" r="30" fill={SKIN} stroke={SKIN_LINE} strokeWidth="5" />
          <circle cx={300 + fw - 2} cy="318" r="30" fill={SKIN} stroke={SKIN_LINE} strokeWidth="5" />
          {look.earrings ? (
            <>
              <circle cx={300 - fw + 4} cy="352" r="8" fill="#fbbf24" stroke="#b45309" strokeWidth="2" />
              <circle cx={300 + fw - 4} cy="352" r="8" fill="#fbbf24" stroke="#b45309" strokeWidth="2" />
            </>
          ) : null}
          <ellipse cx="300" cy="300" rx={fw} ry={fh} fill={`url(#skin-${uid})`} stroke={SKIN_LINE} strokeWidth="6" />

          {/* Beard grows from the jaw; the mouth is drawn over it. */}
          {look.facialHair === 'beard' ? (
            <g clipPath={`url(#face-${uid})`}>
              <path
                d="M140 300 C140 420 214 490 300 492 C386 490 460 420 460 300 C440 366 412 386 372 396 C350 384 250 384 228 396 C188 386 160 366 140 300 Z"
                fill={look.beard}
              />
            </g>
          ) : null}
          {look.facialHair === 'goatee' ? (
            <path d="M262 428 Q300 418 338 428 Q330 466 300 470 Q270 466 262 428 Z" fill={look.beard} />
          ) : null}
          {look.facialHair === 'stubble' ? (
            <g clipPath={`url(#face-${uid})`}>
              <path d="M140 330 C150 430 220 470 300 470 C380 470 450 430 460 330 C440 392 400 400 300 398 C200 400 160 392 140 330 Z" fill={look.beard} opacity="0.2" />
            </g>
          ) : null}

          {/* Age lines. */}
          {wr > 0 ? (
            <g fill="none" stroke={SKIN_LINE} strokeLinecap="round" opacity={0.25 + wr * 0.55} strokeWidth="4">
              <path d={`M236 ${look.hairStyle === 'balding' ? 196 : 218} Q300 ${look.hairStyle === 'balding' ? 188 : 210} 364 ${look.hairStyle === 'balding' ? 196 : 218}`} />
              {look.hairStyle === 'balding' ? <path d="M246 178 Q300 170 354 178" /> : null}
              {wr > 0.5 ? <path d="M262 232 Q300 226 338 232" opacity="0.7" /> : null}
              <path d="M262 368 Q246 392 256 424" />
              <path d="M338 368 Q354 392 344 424" />
              {wr > 0.4 ? (
                <>
                  <path d="M196 292 L176 286 M196 304 L172 304 M196 316 L176 324" />
                  <path d="M404 292 L424 286 M404 304 L428 304 M404 316 L424 324" />
                  <path d="M220 346 Q242 356 264 346" opacity="0.6" />
                  <path d="M336 346 Q358 356 380 346" opacity="0.6" />
                </>
              ) : null}
            </g>
          ) : null}

          {/* Hair, with a cowlick that bounces with the voice. */}
          {hairParts.front}

          {/* Brows */}
          <path
            d="M208 248 Q242 230 276 246"
            fill="none"
            stroke={browColor}
            strokeWidth={look.browWeight}
            strokeLinecap="round"
            transform={`translate(0 ${-browLift}) rotate(${emotion.browTilt} 242 244)`}
          />
          <path
            d="M324 246 Q358 230 392 248"
            fill="none"
            stroke={browColor}
            strokeWidth={look.browWeight}
            strokeLinecap="round"
            transform={`translate(0 ${-browLift - (phase === 'rising' ? 8 : 0)}) rotate(${-emotion.browTilt} 358 244)`}
          />

          {/* Eyes */}
          {eyeXs.map((cx, i) => (
            <g key={cx} transform={`translate(${cx} 304) scale(1 ${Math.max(0.06, eyeScale)}) translate(${-cx} -304)`}>
              <ellipse cx={cx} cy="304" rx={31 * k} ry={35 * k} fill="#ffffff" stroke={SKIN_LINE} strokeWidth="4" />
              <circle cx={cx + gaze.x} cy={304 + gaze.y} r={20 * k} fill={look.eye} />
              <circle cx={cx + gaze.x} cy={304 + gaze.y} r={11 * k} fill="#0b0b0b" />
              <circle cx={cx + gaze.x - 7 * k} cy={304 + gaze.y - 8 * k} r={6.5 * k} fill="#ffffff" />
              <circle cx={cx + gaze.x + 6 * k} cy={304 + gaze.y + 7 * k} r={3 * k} fill="#ffffff" opacity="0.8" />
              {wr > 0.5 ? (
                <g clipPath={`url(#eye-${uid}-${cx})`}>
                  <path d={`M${cx - 36 * k} ${304 - 40 * k} H${cx + 36 * k} V${304 - 14 * k} Q${cx} ${304 - 6 * k} ${cx - 36 * k} ${304 - 14 * k} Z`} fill={SKIN} />
                  <path d={`M${cx - 33 * k} ${304 - 14 * k} Q${cx} ${304 - 6 * k} ${cx + 33 * k} ${304 - 14 * k}`} fill="none" stroke={SKIN_LINE} strokeWidth="4" strokeLinecap="round" />
                </g>
              ) : null}
              {look.lashes ? (
                <path
                  d={`M${cx - 33 * k} ${304 - 8 * k} Q${cx} ${304 - 46 * k} ${cx + 33 * k} ${304 - 8 * k} M${cx + (i === 0 ? -31 : 31) * k} ${304 - 12 * k} l${(i === 0 ? -9 : 9) * k} ${-9 * k}`}
                  fill="none"
                  stroke={look.hair}
                  strokeWidth="6"
                  strokeLinecap="round"
                />
              ) : null}
            </g>
          ))}

          {/* Glasses */}
          {lens ? (
            <g fill="#ffffff" fillOpacity="0.14" stroke={lens.color} strokeWidth="6" strokeLinejoin="round" strokeLinecap="round">
              {eyeXs.map((cx) =>
                lens.shape === 'round' ? (
                  <circle key={cx} cx={cx} cy="306" r={48} />
                ) : (
                  <rect key={cx} x={cx - 50} y={306 - 38} width="100" height="76" rx="16" />
                )
              )}
              <path d="M290 298 Q300 290 310 298" fill="none" />
              <path d="M192 300 L156 292 M408 300 L444 292" fill="none" />
            </g>
          ) : null}

          {/* Nose and cheeks */}
          <path d="M292 352 Q300 362 310 352" fill="none" stroke={SKIN_LINE} strokeWidth="6" strokeLinecap="round" />
          <ellipse cx="200" cy="372" rx="26" ry="15" fill={look.blush} opacity={0.28 + smile * 0.08} />
          <ellipse cx="400" cy="372" rx="26" ry="15" fill={look.blush} opacity={0.28 + smile * 0.08} />

          {look.facialHair === 'mustache' ? (
            <path
              d={`M300 376 Q262 362 228 392 Q262 398 300 384 Q338 398 372 392 Q338 362 300 376 Z`}
              fill={look.beard}
            />
          ) : null}

          {/* Mouth: interior, teeth and tongue clipped to the lip shape. */}
          <path d={mouthPath} fill="#5b1226" />
          <g clipPath={`url(#mouth-${uid})`}>
            <rect x={mx - 60} y={cornerY - 30} width="120" height={36 + depth * 0.15} rx="8" fill="#ffffff" />
            <ellipse cx={mx} cy={cornerY + curve * 0.5 + depth * 1.05} rx={width * 0.34} ry={8 + depth * 0.3} fill="#f472b6" />
          </g>
          {look.lip ? <path d={mouthPath} fill="none" stroke={look.lip} strokeWidth="11" strokeLinejoin="round" /> : null}
          <path d={mouthPath} fill="none" stroke="#3b0a17" strokeWidth="5" strokeLinejoin="round" />
        </g>
      </g>
    </svg>
  );
};
