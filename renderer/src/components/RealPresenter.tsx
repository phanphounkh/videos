/**
 * The semi-realistic illustrated host ("real" avatars).
 *
 * Same animation API as the cartoon Presenter (lip-sync, nods, blinks, gestures, cue
 * pointing, celebration wave; all from hostMotion.ts), drawn with natural proportions:
 * shaded skin, defined brows, lids and lashes, a modelled nose, natural lips, ears, a neck
 * with shadow, hair with highlights, business-casual clothes and properly drawn hands.
 * Illustrated rather than photographic, and a pure function of the frame.
 */
import React, { useId } from 'react';
import { mixHex, type AvatarSpec } from '../avatars';
import { useHostMotion, type HostProps, type Pose } from './hostMotion';

type Props = HostProps & { spec: AvatarSpec };

const CX = 300;
/** The figure is drawn a little larger than life so the face reads on the stage. */
const FIGURE_SCALE = 1.16;
const UPPER = 118;
const FORE = 106;

const SHOULDER_HALF = { slim: 164, regular: 178, broad: 194 } as const;

/** Tiny deterministic generator, so stubble is the same on every frame and render. */
const rng = (seed: number) => () => {
  seed = (seed * 16807) % 2147483647;
  return (seed - 1) / 2147483646;
};

type Pt = { x: number; y: number };

/** One drawn hand: local +y runs along the forearm. */
const Hand: React.FC<{ side: 'L' | 'R'; pointing: boolean; skin: string; line: string; angle: number; at: Pt; id: string }> = ({
  side,
  pointing,
  skin,
  line,
  angle,
  at,
  id
}) => {
  const thumb = side === 'R' ? -1 : 1;
  const fingers = pointing
    ? [
        { x: thumb * 14.5, d: 0, len: 52 },
        { x: thumb * 4.5, d: 0, len: 12 },
        { x: -thumb * 5.5, d: 0, len: 12 },
        { x: -thumb * 15.5, d: 0, len: 10 }
      ]
    : [
        { x: thumb * 15.5, d: thumb * 3, len: 31 },
        { x: thumb * 5.2, d: thumb * 1, len: 36 },
        { x: -thumb * 5.2, d: -thumb * 1, len: 34 },
        { x: -thumb * 15.5, d: -thumb * 3, len: 26 }
      ];
  const parts = (pass: 'line' | 'fill') => {
    const stroke = pass === 'line' ? line : skin;
    const extra = pass === 'line' ? 3.4 : 0;
    return (
      <>
        {fingers.map((f, i) => (
          <path
            key={i}
            d={`M${f.x} 42 L${f.x + f.d} ${42 + f.len}`}
            stroke={stroke}
            strokeWidth={10.6 + extra}
            strokeLinecap="round"
            fill="none"
          />
        ))}
        <path
          d={`M${thumb * 17} 16 Q${thumb * 30} 28 ${thumb * (pointing ? 24 : 34)} ${pointing ? 40 : 46}`}
          stroke={stroke}
          strokeWidth={11.5 + extra}
          strokeLinecap="round"
          fill="none"
        />
        <path
          d="M-21 -2 C-26 16 -25 36 -17 50 Q0 58 17 50 C25 36 26 16 21 -2 Z"
          fill={pass === 'line' ? line : `url(#palm-${id})`}
          stroke={pass === 'line' ? line : 'none'}
          strokeWidth={extra}
          strokeLinejoin="round"
        />
      </>
    );
  };
  return (
    <g transform={`translate(${at.x} ${at.y}) rotate(${angle}) scale(0.94)`}>
      {parts('line')}
      {parts('fill')}
      {/* Knuckle and thumb creases give the hand its structure. */}
      <path d={`M${thumb * 17} 16 Q${thumb * 8} 30 ${thumb * 5} 44`} stroke={line} strokeWidth="1.6" fill="none" opacity="0.5" strokeLinecap="round" />
      {pointing ? null : <path d="M-14 46 Q0 50 14 46" stroke={line} strokeWidth="1.5" fill="none" opacity="0.45" />}
    </g>
  );
};

const Arm: React.FC<{
  side: 'L' | 'R';
  pose: Pose;
  shoulder: Pt;
  sleeve: string;
  sleeveDark: string;
  sleeveLight: string;
  cuff: string;
  skin: string;
  line: string;
  id: string;
}> = ({ side, pose, shoulder, sleeve, sleeveDark, sleeveLight, cuff, skin, line, id }) => {
  const sign = side === 'L' ? -1 : 1;
  const rad = (deg: number) => (deg * Math.PI) / 180;
  const elbow = {
    x: shoulder.x + sign * Math.sin(rad(pose.a)) * UPPER,
    y: shoulder.y + Math.cos(rad(pose.a)) * UPPER
  };
  const foreAngle = pose.a + pose.b;
  const dir = { x: sign * Math.sin(rad(foreAngle)), y: Math.cos(rad(foreAngle)) };
  const wrist = { x: elbow.x + dir.x * FORE, y: elbow.y + dir.y * FORE };
  const cuffStart = { x: wrist.x - dir.x * 13, y: wrist.y - dir.y * 13 };
  const handAngle = (Math.atan2(-dir.x, dir.y) * 180) / Math.PI;
  const seg = (a: Pt, b: Pt) => `M${a.x} ${a.y} L${b.x} ${b.y}`;
  return (
    <g>
      <path d={seg(shoulder, elbow)} stroke={sleeveDark} strokeWidth={62} strokeLinecap="round" />
      <path d={seg(elbow, cuffStart)} stroke={sleeveDark} strokeWidth={52} strokeLinecap="round" />
      <path d={seg(shoulder, elbow)} stroke={sleeve} strokeWidth={57} strokeLinecap="round" />
      <path d={seg(elbow, cuffStart)} stroke={sleeve} strokeWidth={47} strokeLinecap="round" />
      <circle cx={elbow.x} cy={elbow.y} r={23.5} fill={sleeve} />
      {/* Soft light along the sleeve, and the cuff of the shirt underneath. */}
      <path d={seg(shoulder, elbow)} stroke={sleeveLight} strokeWidth={14} strokeLinecap="round" opacity="0.28" transform={`translate(${-sign * 8} -4)`} />
      <path d={seg(elbow, cuffStart)} stroke={sleeveLight} strokeWidth={10} strokeLinecap="round" opacity="0.22" transform={`translate(${-sign * 6} -3)`} />
      <path d={seg(cuffStart, wrist)} stroke={cuff} strokeWidth={40} strokeLinecap="butt" />
      <Hand side={side} pointing={!!pose.point} skin={skin} line={line} angle={handAngle} at={wrist} id={id} />
    </g>
  );
};

export const RealPresenter: React.FC<Props> = (props) => {
  const { phase, theme, viewBox, spec } = props;
  const look = spec.look;
  const female = spec.gender === 'female';
  const age = spec.age;
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '');
  const m = useHostMotion(props);
  const { emotion, squash, breath, nod, tilt, gaze, browLift, smile, open } = m;

  const wr = look.wrinkles;
  const SK = look.skin;
  const SK_L = look.skinLight;
  const SK_D = look.skinLine;
  const darkSkin = mixHex(SK, '#3a1808', 0.55);

  // ---- proportions ----------------------------------------------------------------
  const W = (female ? 96 : 104) * look.faceWidth * (age === 'young' ? 0.97 : 1) + (age === 'old' && !female ? 2 : 0);
  const J = female ? (age === 'young' ? 64 : 70) : age === 'young' ? 72 : 79;
  const chinY = female ? 430 : 436;
  const chinW = female ? 26 : 34;
  const topY = look.hairStyle === 'balding' ? 134 : 150;
  const eyeR = 24 * look.eyeScale * (age === 'young' ? (female ? 1.14 : 1.08) : 1) * (age === 'old' ? 0.94 : 1);
  const nw = female ? 31 : 39; // neck half-width
  const sx = SHOULDER_HALF[look.build];
  const shoulderY = 604;
  const leftShoulder = { x: CX - sx + 10, y: shoulderY };
  const rightShoulder = { x: CX + sx - 10, y: shoulderY };
  const ex = 47; // eye centre offset
  const eyeY = 292;
  const mouthY = 392;

  const faceHalf = (s: 1 | -1) => {
    const X = (d: number) => CX + s * d;
    return (
      `C${X(W * 0.6)} ${topY} ${X(W)} ${topY + 52} ${X(W)} 286 ` +
      `C${X(W)} 338 ${X(J + 9)} 374 ${X(J)} 398 ` +
      `C${X(J * 0.8)} 428 ${X(chinW)} ${chinY} ${CX} ${chinY}`
    );
  };
  // right side down to the chin, then the left side back up (built mirrored)
  const facePath =
    `M${CX} ${topY} ${faceHalf(1)} ` +
    `C${CX - chinW} ${chinY} ${CX - J * 0.8} 428 ${CX - J} 398 C${CX - J - 9} 374 ${CX - W} 338 ${CX - W} 286 C${CX - W} ${topY + 52} ${CX - W * 0.6} ${topY} ${CX} ${topY} Z`;

  // ---- clothes ----------------------------------------------------------------------
  const outfit = look.outfit;
  const cloth = outfit.color ?? mixHex(theme.shade, '#ffffff', 0.15);
  const clothLight = mixHex(cloth, '#ffffff', 0.22);
  const clothDark = mixHex(cloth, '#0a0a14', 0.28);
  const themed = mixHex(cloth, theme.glow, 0.07);
  const torso =
    `M${CX - nw * 1.15} 528 C${CX - sx * 0.55} 540 ${CX - sx - 8} 552 ${CX - sx - 16} 604 ` +
    `C${CX - sx - 26} 660 ${CX - sx - 30} 720 ${CX - sx - 30} 790 L${CX + sx + 30} 790 ` +
    `C${CX + sx + 30} 720 ${CX + sx + 26} 660 ${CX + sx + 16} 604 C${CX + sx + 8} 552 ${CX + sx * 0.55} 540 ${CX + nw * 1.15} 528 Z`;

  // ---- mouth ------------------------------------------------------------------------
  const mw = 60 + smile * 9 - open * 12;
  const lift = smile * 4.2;
  const cy = mouthY - lift + open * 1.5;
  const gap = open * 32;
  const L = { x: CX - mw / 2, y: cy };
  const R = { x: CX + mw / 2, y: cy };
  const upThick = female ? 11 : 9.5;
  const loThick = female ? 12 : 10.5;
  const lipTop =
    `M${L.x} ${L.y} C${CX - mw * 0.3} ${cy - upThick - 1} ${CX - 7} ${cy - upThick - 1} ${CX} ${cy - upThick + 3} ` +
    `C${CX + 7} ${cy - upThick - 1} ${CX + mw * 0.3} ${cy - upThick - 1} ${R.x} ${R.y}`;
  const mouthLine = `Q${CX} ${cy + 1.5 + lift * 0.4} ${L.x} ${L.y}`; // R -> L (upper lip underside)
  const openingTop = `M${L.x} ${L.y} Q${CX} ${cy + 1.5 + lift * 0.4} ${R.x} ${R.y}`;
  const openingBottom = `Q${CX} ${cy + 2 * gap + 2} ${L.x} ${L.y}`;
  const opening = `${openingTop} ${openingBottom} Z`;
  const lowerLip =
    `M${L.x} ${L.y} Q${CX} ${cy + 2 * gap + 2} ${R.x} ${R.y} ` +
    `Q${CX} ${cy + 2 * gap + 2 + loThick * 2 + 2} ${L.x} ${L.y} Z`;
  const upperLip = `${lipTop} ${mouthLine} Z`;
  const lipColor = look.lip ?? mixHex(SK, '#a04a46', 0.6);
  const lipDark = mixHex(lipColor, '#2a0a10', 0.35);
  const lipLight = mixHex(lipColor, '#ffffff', 0.12);

  // ---- hair (see hair() below) ------------------------------------------------------
  const hairBase = look.hair;
  const hairHi = look.hairHi;

  const headTransform = `translate(0 ${breath * 0.9 + nod * 0.7}) rotate(${tilt * 0.8} 300 460)`;

  const strokesFor = (d: string[], color: string, width: number, opacity: number) =>
    d.map((p, i) => <path key={i} d={p} fill="none" stroke={color} strokeWidth={width} strokeLinecap="round" opacity={opacity} />);

  type Hair = { back: React.ReactNode; front: React.ReactNode };
  const hair = (): Hair => {
    const style = look.hairStyle;
    const fill = `url(#hair-${uid})`;
    const hl = (d: string[], op = 0.5) => strokesFor(d, hairHi, 2.4, op);
    const shade = (d: string[], op = 0.35) => strokesFor(d, mixHex(hairBase, '#000000', 0.5), 2.2, op);
    switch (style) {
      case 'balding':
        return {
          back: null,
          front: (
            <>
              <path d="M196 276 C188 252 192 226 206 208 C206 228 212 244 224 256 C218 268 208 278 200 288 Z" fill={fill} />
              <path d="M404 276 C412 252 408 226 394 208 C394 228 388 244 376 256 C382 268 392 278 400 288 Z" fill={fill} />
              {hl(['M200 220 Q202 246 214 262', 'M400 220 Q398 246 386 262'], 0.7)}
              <ellipse cx="268" cy="176" rx="36" ry="11" fill="#ffffff" opacity="0.16" transform="rotate(-16 268 176)" />
            </>
          )
        };
      case 'sidepart':
        return {
          back: null,
          front: (
            <>
              <path
                d="M194 276 C182 214 192 166 240 142 C274 124 344 122 378 142 C414 164 418 218 404 276 C400 248 392 230 376 220 C352 232 304 214 262 198 C240 204 216 236 206 254 C200 260 197 268 194 276 Z"
                fill={fill}
              />
              <path d="M392 150 C408 180 410 230 404 276" fill="none" stroke={mixHex(hairBase, '#000', 0.4)} strokeWidth="10" opacity="0.25" />
              {hl(['M252 140 Q262 176 240 206', 'M262 134 Q330 120 388 156', 'M284 142 Q340 132 396 176', 'M232 160 Q244 140 270 134'], 0.5)}
              {shade(['M252 142 Q258 178 238 206'], 0.5)}
            </>
          )
        };
      case 'long':
      case 'ponytail':
        return {
          back: (
            <path
              d="M188 262 C168 160 218 116 300 116 C382 116 432 160 412 262 C424 340 432 424 430 500 C428 560 408 596 384 606 L216 606 C192 596 172 560 170 500 C168 424 176 340 188 262 Z"
              fill={fill}
            />
          ),
          front: (
            <>
              <path d="M300 136 C238 134 192 176 188 252 C184 330 178 420 184 496 C188 540 204 562 224 570 C222 524 214 474 214 414 C214 344 224 284 244 240 C260 206 286 176 300 136 Z" fill={fill} />
              <path d="M300 136 C362 134 408 176 412 252 C416 330 422 420 416 496 C412 540 396 562 376 570 C378 524 386 474 386 414 C386 344 376 284 356 240 C340 206 314 176 300 136 Z" fill={fill} />
              {hl(['M244 158 Q214 220 212 330', 'M260 150 Q226 210 222 300', 'M356 158 Q388 220 388 330', 'M200 300 Q192 400 200 500', 'M400 300 Q408 400 400 500'], 0.35)}
              {shade(['M204 340 Q200 430 206 520', 'M396 340 Q400 430 394 520'], 0.4)}
            </>
          )
        };
      case 'wavy':
        return {
          back: (
            <path
              d="M188 262 C166 160 218 116 300 116 C382 116 434 160 412 262 C424 326 434 380 424 430 C440 462 424 500 438 534 C416 548 394 530 380 512 L220 512 C206 530 184 548 162 534 C176 500 160 462 176 430 C166 380 176 326 188 262 Z"
              fill={fill}
            />
          ),
          front: (
            <>
              <path d="M262 132 C214 142 188 190 188 256 C186 320 172 372 186 420 C196 458 176 492 192 530 C214 536 232 512 224 472 C218 430 214 380 220 336 C226 280 246 232 280 190 C290 168 292 148 262 132 Z" fill={fill} />
              <path d="M262 132 C320 120 400 150 412 252 C418 320 428 372 414 420 C404 458 424 492 408 530 C386 536 368 512 376 472 C382 430 386 380 380 336 C374 290 352 234 322 204 C296 176 282 150 262 132 Z" fill={fill} />
              {hl(['M246 148 Q206 210 208 300', 'M226 380 Q216 440 226 490', 'M374 380 Q384 440 374 490', 'M330 150 Q394 176 402 262'], 0.4)}
              {shade(['M200 340 Q186 420 200 510', 'M400 340 Q414 420 400 510'], 0.4)}
            </>
          )
        };
      case 'bob':
      case 'bun':
        return {
          back: (
            <path
              d="M188 262 C166 160 218 116 300 116 C382 116 434 160 412 262 C422 316 426 380 418 446 C412 480 392 494 366 490 L234 490 C208 494 188 480 182 446 C174 380 178 316 188 262 Z"
              fill={fill}
            />
          ),
          front: (
            <>
              <path d="M262 132 C214 142 188 190 188 256 C186 316 180 380 188 436 C196 462 218 468 236 452 C222 414 218 372 224 332 C230 280 248 232 280 190 C290 168 290 148 262 132 Z" fill={fill} />
              <path d="M262 132 C320 120 400 150 412 252 C414 316 420 380 412 436 C404 462 382 468 364 452 C378 414 382 372 376 332 C370 290 350 238 320 206 C296 176 282 150 262 132 Z" fill={fill} />
              {hl(['M246 148 Q206 210 208 300', 'M330 150 Q394 176 402 262', 'M204 360 Q204 410 214 440', 'M396 360 Q396 410 386 440'], 0.45)}
              {shade(['M198 340 Q194 400 204 450', 'M402 340 Q406 400 396 450'], 0.3)}
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
              <path
                d="M196 274 C184 214 192 164 238 142 C272 124 342 122 376 142 C414 164 418 218 404 274 C398 246 390 226 376 212 C348 224 322 206 298 192 C272 206 234 210 214 232 C206 244 200 260 196 274 Z"
                fill={fill}
              />
              {hl(['M228 158 Q266 134 318 138', 'M250 150 Q300 128 352 144', 'M222 190 Q232 160 262 148', 'M300 142 Q360 136 392 176', 'M214 224 Q218 190 240 170'], 0.5)}
              {shade(['M232 214 Q262 206 296 206', 'M356 212 Q380 220 396 236'], 0.35)}
            </>
          )
        };
    }
  };
  const hairParts = hair();

  // ---- facial hair --------------------------------------------------------------------
  const beardColor = look.beard;
  const stubble = (() => {
    const r = rng(7 + spec.id.length * 13);
    const dots: React.ReactNode[] = [];
    for (let i = 0; i < 190; i++) {
      const x = CX + (r() * 2 - 1) * (W + 4);
      const y = 350 + r() * (chinY - 340);
      // keep dots to the lower face and sides, away from the lips
      const dxm = Math.abs(x - CX);
      if (y < 372 && dxm < 70) continue;
      if (y < 372 + (dxm > 60 ? 0 : 0) && dxm < 78 && y < 380) continue;
      if (Math.abs(y - mouthY) < 12 && dxm < 38) continue;
      dots.push(<circle key={i} cx={x} cy={y} r={0.9 + r() * 0.5} fill={beardColor} opacity={0.18 + r() * 0.22} />);
    }
    return dots;
  })();

  const beardShape = `M${CX - W - 4} 322 C${CX - W - 6} 392 ${CX - J - 8} 440 ${CX - 30} ${chinY + 30} C${CX - 10} ${chinY + 38} ${CX + 10} ${chinY + 38} ${CX + 30} ${chinY + 30} C${CX + J + 8} 440 ${CX + W + 6} 392 ${CX + W + 4} 322 C${CX + W - 8} 352 ${CX + J + 2} 372 ${CX + 52} 380 C${CX + 40} 372 ${CX + 18} 372 ${CX} 376 C${CX - 18} 372 ${CX - 40} 372 ${CX - 52} 380 C${CX - J - 2} 372 ${CX - W + 8} 352 ${CX - W - 4} 322 Z`;

  const lensColor = look.glasses?.color ?? '#333';

  // ---- eyes ----------------------------------------------------------------------------
  const eye = (side: -1 | 1) => {
    const s = side;
    const e = eyeR;
    const gx = Math.max(-5, Math.min(5, gaze.x * 0.5));
    const gy = Math.max(-3, Math.min(3, gaze.y * 0.4));
    const upper = `M${s * e} -2 C${s * e * 0.55} ${-e * 0.72} ${-s * e * 0.45} ${-e * 0.86} ${-s * e} ${e * 0.1}`;
    const lowerBack = `C${-s * e * 0.5} ${e * 0.66} ${s * e * 0.55} ${e * 0.62} ${s * e} -2`;
    const shape = `${upper} ${lowerBack} Z`;
    // Surprise widens the eye a little; a blink (m.lid) closes it.
    const lidScale = Math.max(0.05, (1 + (emotion.eyes - 1) * 0.55) * m.lid);
    const droop = age === 'old' ? 0.18 : age === 'adult' ? 0.06 : 0;
    const cxEye = CX + s * ex;
    return (
      <g transform={`translate(${cxEye} ${eyeY})`}>
        {/* Socket shadow and lid crease stay still while the eye blinks. */}
        <ellipse cx={0} cy={-3} rx={e * 1.45} ry={e * 0.9} fill={SK_D} opacity={0.14 + wr * 0.05} filter={`url(#blur6-${uid})`} />
        <path
          d={`M${s * (e + 3)} ${-e * 0.42 - 2} Q${s * 2} ${-e * 1.38 - droop * 6} ${-s * (e + 3)} ${-e * 0.3}`}
          fill="none"
          stroke={SK_D}
          strokeWidth={2.2}
          opacity={0.55}
          strokeLinecap="round"
        />
        <g transform={`scale(1 ${lidScale})`}>
          <clipPath id={`eyeclip-${uid}-${side}`}>
            <path d={shape} />
          </clipPath>
          <path d={shape} fill="#efe7de" />
          <g clipPath={`url(#eyeclip-${uid}-${side})`}>
            <circle cx={gx} cy={gy - 1} r={e * 0.5} fill={look.eye} />
            <circle cx={gx} cy={gy - 1} r={e * 0.5} fill="none" stroke={mixHex(look.eye, '#000', 0.5)} strokeWidth="1.6" />
            <circle cx={gx} cy={gy - 1} r={e * 0.24} fill="#0a0808" />
            <circle cx={gx - e * 0.16} cy={gy - 1 - e * 0.18} r={e * 0.11} fill="#fff" opacity="0.95" />
            <circle cx={gx + e * 0.14} cy={gy - 1 + e * 0.14} r={e * 0.05} fill="#fff" opacity="0.6" />
            {/* upper lid shadow on the eyeball */}
            <path d={`${upper} L${-s * e} ${-e} L${s * e} ${-e} Z`} fill="#3a1a10" opacity="0.22" />
            <ellipse cx={0} cy={-e * 0.6} rx={e} ry={e * 0.28} fill="#3a1a10" opacity="0.18" filter={`url(#blur2-${uid})`} />
          </g>
          {/* lash line */}
          <path d={upper} fill="none" stroke="#1a0f0c" strokeWidth={look.lashes ? 4.4 : 3} strokeLinecap="round" />
          {look.lashes ? (
            <>
              <path d={`M${s * e} -2 q${s * 8} ${-4} ${s * 10} ${-12}`} fill="none" stroke="#1a0f0c" strokeWidth="3" strokeLinecap="round" />
              <path d={`M${s * e * 0.72} ${-e * 0.52} q${s * 6} ${-5} ${s * 7} ${-12}`} fill="none" stroke="#1a0f0c" strokeWidth="2.4" strokeLinecap="round" />
            </>
          ) : null}
          <path d={`M${-s * e} -2 C${-s * e * 0.5} ${e * 0.66} ${s * e * 0.55} ${e * 0.62} ${s * e} -2`} fill="none" stroke={SK_D} strokeWidth="1.4" opacity="0.5" />
        </g>
        {age !== 'young' ? (
          <path d={`M${-e * 0.9} ${e * 0.9} Q0 ${e * 1.35} ${e * 0.9} ${e * 0.9}`} fill="none" stroke={SK_D} strokeWidth={2} opacity={0.2 + wr * 0.3} />
        ) : null}
      </g>
    );
  };

  const brow = (side: -1 | 1) => {
    const s = side;
    const th = female ? 5.4 : age === 'old' ? 10.5 : 8.2;
    const lifted = browLift * 0.5;
    const tilt2 = side === -1 ? emotion.browTilt * 0.5 : -emotion.browTilt * 0.5;
    const extra = side === 1 && phase === 'rising' ? -4 : 0;
    const bx = CX + s * (ex + 2);
    return (
      <path
        transform={`translate(${bx} ${eyeY - 29 - lifted + extra}) rotate(${tilt2})`}
        d={`M${-s * 25} 7 C${-s * 12} -5 ${s * 6} ${-11 - (female ? 2 : 0)} ${s * 29} 2 C${s * 8} ${-11 + th} ${-s * 12} ${-4 + th} ${-s * 25} ${7 + th * 1.1} Z`}
        fill={look.brow}
        stroke={look.brow}
        strokeWidth="1.5"
        strokeLinejoin="round"
        opacity="0.95"
      />
    );
  };

  const glasses = look.glasses
    ? [-1, 1].map((s) => {
        const gx = CX + s * ex;
        const round = look.glasses!.shape === 'round';
        return (
          <g key={s}>
            {round ? (
              <circle cx={gx} cy={eyeY + 1} r={32} fill="#cfe8ff" fillOpacity="0.1" stroke={lensColor} strokeWidth="3.4" />
            ) : (
              <rect x={gx - 38} y={eyeY - 24} width="76" height="52" rx="12" fill="#cfe8ff" fillOpacity="0.1" stroke={lensColor} strokeWidth="3.4" />
            )}
            <path d={`M${gx - 22} ${eyeY + 18} L${gx - 4} ${eyeY - 18}`} stroke="#ffffff" strokeWidth="5" opacity="0.18" strokeLinecap="round" />
          </g>
        );
      })
    : null;

  const sleeve = `url(#cloth-${uid})`;
  const cuff = outfit.inner;

  return (
    <svg viewBox={viewBox ?? '0 0 600 760'} width="100%" height="100%" aria-label="Storyteller" style={{ overflow: 'visible' }}>
      <defs>
        <filter id={`blur6-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="6" />
        </filter>
        <filter id={`blur3-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" />
        </filter>
        <filter id={`blur1-${uid}`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="0.9" />
        </filter>
        <filter id={`blur2-${uid}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="1.6" />
        </filter>
        <radialGradient id={`skin-${uid}`} cx="0.42" cy="0.34" r="0.78">
          <stop offset="0" stopColor={SK_L} />
          <stop offset="0.55" stopColor={SK} />
          <stop offset="1" stopColor={mixHex(SK, SK_D, 0.45)} />
        </radialGradient>
        <linearGradient id={`neck-${uid}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor={mixHex(SK, SK_D, 0.35)} />
          <stop offset="0.35" stopColor={SK} />
          <stop offset="1" stopColor={mixHex(SK, SK_D, 0.7)} />
        </linearGradient>
        <linearGradient id={`hair-${uid}`} x1="0.2" y1="0" x2="0.8" y2="1">
          <stop offset="0" stopColor={mixHex(hairBase, hairHi, 0.55)} />
          <stop offset="0.5" stopColor={hairBase} />
          <stop offset="1" stopColor={mixHex(hairBase, '#000000', 0.25)} />
        </linearGradient>
        <linearGradient id={`cloth-${uid}`} gradientUnits="userSpaceOnUse" x1="200" y1="520" x2="400" y2="800">
          <stop offset="0" stopColor={mixHex(themed, '#ffffff', 0.06)} />
          <stop offset="1" stopColor={mixHex(themed, '#0a0a14', 0.3)} />
        </linearGradient>
        <linearGradient id={`volume-${uid}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.12" />
          <stop offset="0.5" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="1" stopColor="#000000" stopOpacity="0.26" />
        </linearGradient>
        <radialGradient id={`palm-${uid}`} cx="0.4" cy="0.35" r="0.8">
          <stop offset="0" stopColor={SK_L} />
          <stop offset="1" stopColor={SK} />
        </radialGradient>
        <linearGradient id={`faceSide-${uid}`} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.1" />
          <stop offset="0.45" stopColor="#ffffff" stopOpacity="0" />
          <stop offset="0.8" stopColor={SK_D} stopOpacity="0.16" />
          <stop offset="1" stopColor={SK_D} stopOpacity="0.5" />
        </linearGradient>
        <linearGradient id={`jaw-${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0.6" stopColor={SK_D} stopOpacity="0" />
          <stop offset="1" stopColor={SK_D} stopOpacity="0.35" />
        </linearGradient>
        <linearGradient id={`lipUp-${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={mixHex(lipColor, '#4a1520', 0.2)} />
          <stop offset="1" stopColor={lipDark} />
        </linearGradient>
        <linearGradient id={`lipLo-${uid}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={lipColor} />
          <stop offset="1" stopColor={lipLight} />
        </linearGradient>
        <clipPath id={`face-${uid}`}>
          <path d={facePath} />
        </clipPath>
        <clipPath id={`mouth-${uid}`}>
          <path d={opening} />
        </clipPath>
        <clipPath id={`neckclip-${uid}`}>
          <rect x={CX - nw} y="380" width={nw * 2} height="150" />
        </clipPath>
        <clipPath id={`torso-${uid}`}>
          <path d={torso} />
        </clipPath>
      </defs>

      <g transform={`translate(300 760) scale(${FIGURE_SCALE}) translate(-300 -760)`}>
      <g transform={`translate(300 760) scale(${1 / squash} ${squash}) translate(-300 -760) translate(0 ${breath * 0.5})`}>
        {/* Long hair falls behind the shoulders. */}
        <g transform={headTransform}>{hairParts.back}</g>

        <g transform="translate(0 -28)">
        {/* Neck */}
        <path d={`M${CX - nw} 396 L${CX - nw - 2} 556 L${CX + nw + 2} 556 L${CX + nw} 396 Z`} fill={`url(#neck-${uid})`} />

        {/* Torso and garment */}
        <path d={torso} fill={`url(#cloth-${uid})`} />
        <g clipPath={`url(#torso-${uid})`}>
          <rect x="0" y="500" width="600" height="300" fill={`url(#volume-${uid})`} />
          {/* inner shirt / blouse */}
          {outfit.kind === 'blazer' || outfit.kind === 'cardigan' ? (
            <path
              d={`M${CX - 56} 520 C${CX - 40} 600 ${CX - 22} 680 ${CX - 26} 800 L${CX + 26} 800 C${CX + 22} 680 ${CX + 40} 600 ${CX + 56} 520 Z`}
              fill={outfit.inner}
            />
          ) : null}
          {outfit.kind === 'blazer' ? (
            <>
              <path d={`M${CX - 56} 520 L${CX} 700 L${CX + 56} 520 Z`} fill={outfit.inner} />
              <path d={`M${CX - 56} 520 L${CX} 700 L${CX + 56} 520 Z`} fill="#000" opacity="0.06" />
            </>
          ) : null}
          {outfit.kind === 'cardigan' ? (
            <path d={`M${CX - 56} 520 Q${CX} 640 ${CX + 56} 520 Z`} fill={outfit.inner} />
          ) : null}
        </g>
        {/* skin notch of the open collar / neckline */}
        {outfit.kind === 'blouse' ? (
          <>
            <path d={`M${CX - nw - 6} 528 Q${CX} 622 ${CX + nw + 6} 528 Z`} fill={SK} />
            <path d={`M${CX - nw - 6} 528 Q${CX} 622 ${CX + nw + 6} 528`} fill="none" stroke={mixHex(outfit.inner, '#000', 0.12)} strokeWidth="5" strokeLinecap="round" />
            <path d={`M${CX - nw - 4} 534 Q${CX} 606 ${CX + nw + 4} 534`} fill={SK_D} opacity="0.18" filter={`url(#blur3-${uid})`} />
          </>
        ) : (
          <>
            <path d={`M${CX - nw - 4} 526 L${CX} ${female ? 612 : 596} L${CX + nw + 4} 526 Z`} fill={SK} />
            <path d={`M${CX - nw - 2} 528 Q${CX} ${female ? 566 : 556} ${CX + nw + 2} 528 L${CX + nw} 526 L${CX - nw} 526 Z`} fill={darkSkin} opacity="0.3" filter={`url(#blur3-${uid})`} />
          </>
        )}
        {outfit.kind === 'blazer' ? (
          <>
            {/* collar wings of the shirt */}
            <path d={`M${CX - nw - 8} 516 L${CX} ${female ? 616 : 600} L${CX - 80} 586 L${CX - 56} 520 Z`} fill={outfit.inner} stroke="#00000018" strokeWidth="2" strokeLinejoin="round" />
            <path d={`M${CX + nw + 8} 516 L${CX} ${female ? 616 : 600} L${CX + 80} 586 L${CX + 56} 520 Z`} fill={outfit.inner} stroke="#00000018" strokeWidth="2" strokeLinejoin="round" />
            {/* lapels */}
            <path d={`M${CX - 70} 514 L${CX - 14} 704 L${CX - 82} 716 L${CX - 130} 590 Z`} fill={clothDark} stroke="#ffffff22" strokeWidth="2" strokeLinejoin="round" />
            <path d={`M${CX + 70} 514 L${CX + 14} 704 L${CX + 82} 716 L${CX + 130} 590 Z`} fill={clothDark} stroke="#ffffff22" strokeWidth="2" strokeLinejoin="round" />
            <path d={`M${CX - 14} 704 L${CX - 12} 800 M${CX + 14} 704 L${CX + 12} 800`} stroke="#00000030" strokeWidth="4" />
            {!female ? <circle cx={CX + 4} cy={744} r="6" fill={clothDark} stroke="#00000033" strokeWidth="2" /> : null}
          </>
        ) : null}
        {outfit.kind === 'cardigan' ? (
          <>
            <path d={`M${CX - 60} 524 Q${CX - 14} 650 ${CX - 30} 800`} fill="none" stroke={clothDark} strokeWidth="12" strokeLinecap="round" opacity="0.7" />
            <path d={`M${CX + 60} 524 Q${CX + 14} 650 ${CX + 30} 800`} fill="none" stroke={clothDark} strokeWidth="12" strokeLinecap="round" opacity="0.7" />
            {[680, 730].map((y) => (
              <circle key={y} cx={CX - 24} cy={y} r="6" fill={outfit.inner} stroke="#00000033" strokeWidth="2" />
            ))}
          </>
        ) : null}
        {outfit.kind === 'tee' || outfit.kind === 'collar' || outfit.kind === 'scoop' ? (
          <path d={`M${CX - nw - 6} 526 Q${CX} 618 ${CX + nw + 6} 526`} fill="none" stroke={outfit.inner} strokeWidth="9" strokeLinecap="round" />
        ) : null}
        {look.necklace ? (
          <path
            d={`M${CX - nw + 2} 534 Q${CX} ${female ? 618 : 600} ${CX + nw - 2} 534`}
            fill="none"
            stroke={look.necklace}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={age === 'old' ? '0.1 9' : '0.1 9'}
          />
        ) : null}

        <Arm side="L" pose={m.left} shoulder={leftShoulder} sleeve={sleeve} sleeveDark={clothDark} sleeveLight={clothLight} cuff={cuff} skin={SK} line={darkSkin} id={uid} />
        <Arm side="R" pose={m.right} shoulder={rightShoulder} sleeve={sleeve} sleeveDark={clothDark} sleeveLight={clothLight} cuff={cuff} skin={SK} line={darkSkin} id={uid} />

        </g>
        {/* the shadow the chin throws on the neck */}
        <g clipPath={`url(#neckclip-${uid})`}>
          <ellipse cx={CX} cy={chinY + 4 + nod * 0.3} rx={nw + 6} ry={22} fill={darkSkin} opacity="0.5" filter={`url(#blur6-${uid})`} />
        </g>

        {/* Head */}
        <g transform={headTransform}>
          {/* ears */}
          {[-1, 1].map((s) => (
            <g key={s} transform={`translate(${CX + s * (W + 2)} 312)`}>
              <ellipse cx={s * 6} cy={0} rx={13} ry={28} fill={SK} />
              <ellipse cx={s * 6} cy={0} rx={13} ry={28} fill="none" stroke={SK_D} strokeWidth="2" opacity="0.6" />
              <path d={`M${s * 3} -14 Q${s * 12} 0 ${s * 3} 16`} fill="none" stroke={SK_D} strokeWidth="3" opacity="0.5" strokeLinecap="round" />
              {look.earrings ? <circle cx={s * 5} cy={31} r={4.5} fill={look.necklace ?? '#e9c46a'} stroke="#b08a2a" strokeWidth="1.2" /> : null}
            </g>
          ))}

          {/* face */}
          <path d={facePath} fill={`url(#skin-${uid})`} />
          <g clipPath={`url(#face-${uid})`}>
            <rect x={CX - W - 10} y="120" width={W * 2 + 20} height="360" fill={`url(#faceSide-${uid})`} />
            <rect x={CX - W - 10} y="120" width={W * 2 + 20} height="360" fill={`url(#jaw-${uid})`} />
            {/* shadow the hair casts on the forehead */}
            <ellipse cx={CX} cy={look.hairStyle === 'balding' ? 134 : 178} rx={W * 0.95} ry="34" fill={SK_D} opacity={look.hairStyle === 'balding' ? 0.05 : 0.3} filter={`url(#blur6-${uid})`} />
            {/* highlights: forehead, cheekbones, nose, chin */}
            <ellipse cx={CX - 8} cy={look.hairStyle === 'balding' ? 188 : 214} rx="46" ry="18" fill="#fff" opacity={age === 'young' ? 0.2 : 0.13} filter={`url(#blur6-${uid})`} />
            <ellipse cx={CX - 58} cy="336" rx="24" ry="13" fill="#fff" opacity={age === 'young' ? 0.18 : 0.1} filter={`url(#blur6-${uid})`} />
            <ellipse cx={CX + 58} cy="336" rx="22" ry="12" fill="#fff" opacity="0.07" filter={`url(#blur6-${uid})`} />
            <ellipse cx={CX} cy={chinY - 18} rx="16" ry="8" fill="#fff" opacity="0.1" filter={`url(#blur3-${uid})`} />
            {/* blush */}
            <ellipse cx={CX - 62} cy="356" rx="28" ry="16" fill={look.blush} opacity={(female ? 0.3 : 0.2) + smile * 0.05} filter={`url(#blur6-${uid})`} />
            <ellipse cx={CX + 62} cy="356" rx="28" ry="16" fill={look.blush} opacity={(female ? 0.26 : 0.17) + smile * 0.05} filter={`url(#blur6-${uid})`} />
            {/* eye bags */}
            {age !== 'young' ? (
              <>
                <ellipse cx={CX - ex} cy={eyeY + 20} rx="26" ry="7" fill={SK_D} opacity={0.12 + wr * 0.12} filter={`url(#blur3-${uid})`} />
                <ellipse cx={CX + ex} cy={eyeY + 20} rx="26" ry="7" fill={SK_D} opacity={0.12 + wr * 0.12} filter={`url(#blur3-${uid})`} />
              </>
            ) : null}
            {/* stubble */}
            {look.facialHair === 'stubble' ? (
              <>
                <path d={beardShape} fill={beardColor} opacity="0.16" filter={`url(#blur3-${uid})`} />
                {stubble}
              </>
            ) : null}
          </g>

          {/* Age lines */}
          {wr > 0 ? (
            <g fill="none" stroke={SK_D} strokeLinecap="round" filter={`url(#blur2-${uid})`} opacity={0.2 + wr * 0.5} strokeWidth="2.4">
              <path d={`M${CX - 46} ${look.hairStyle === 'balding' ? 190 : 214} Q${CX} ${look.hairStyle === 'balding' ? 184 : 208} ${CX + 46} ${look.hairStyle === 'balding' ? 190 : 214}`} />
              {wr > 0.45 ? <path d={`M${CX - 38} ${look.hairStyle === 'balding' ? 206 : 226} Q${CX} ${look.hairStyle === 'balding' ? 200 : 220} ${CX + 38} ${look.hairStyle === 'balding' ? 206 : 226}`} /> : null}
              {wr > 0.7 && look.hairStyle === 'balding' ? <path d={`M${CX - 44} 174 Q${CX} 168 ${CX + 44} 174`} /> : null}
              <path d={`M${CX - 29} 350 Q${CX - 42} 376 ${CX - 36} 404`} strokeWidth={2 + wr * 1.4} />
              <path d={`M${CX + 29} 350 Q${CX + 42} 376 ${CX + 36} 404`} strokeWidth={2 + wr * 1.4} />
              {wr > 0.35 ? (
                <>
                  <path d={`M${CX - ex - 28} ${eyeY - 4} l-12 -5 M${CX - ex - 28} ${eyeY + 3} l-14 2 M${CX - ex - 27} ${eyeY + 10} l-11 8`} />
                  <path d={`M${CX + ex + 28} ${eyeY - 4} l12 -5 M${CX + ex + 28} ${eyeY + 3} l14 2 M${CX + ex + 27} ${eyeY + 10} l11 8`} />
                </>
              ) : null}
              {wr > 0.6 ? (
                <>
                  <path d={`M${CX - 56} 372 Q${CX - 66} 392 ${CX - 54} 414`} opacity="0.7" />
                  <path d={`M${CX + 56} 372 Q${CX + 66} 392 ${CX + 54} 414`} opacity="0.7" />
                </>
              ) : null}
            </g>
          ) : null}
          {smile > 0.9 ? (
            <g fill="none" stroke={SK_D} strokeLinecap="round" opacity={Math.min(0.4, (smile - 0.9) * 0.9 + 0.1)} strokeWidth="2">
              <path d={`M${L.x - 7} ${cy - 8} Q${L.x - 12} ${cy} ${L.x - 6} ${cy + 8}`} />
              <path d={`M${R.x + 7} ${cy - 8} Q${R.x + 12} ${cy} ${R.x + 6} ${cy + 8}`} />
            </g>
          ) : null}

          {/* nose: bridge shadow, tip highlight, nostrils */}
          <g>
            <path d={`M${CX - 11} 294 Q${CX - 15} 330 ${CX - 20} 350`} fill="none" stroke={SK_D} strokeWidth="9" opacity="0.2" strokeLinecap="round" filter={`url(#blur3-${uid})`} />
            <path d={`M${CX + 11} 294 Q${CX + 15} 330 ${CX + 20} 350`} fill="none" stroke={SK_D} strokeWidth="9" opacity="0.28" strokeLinecap="round" filter={`url(#blur3-${uid})`} />
            <ellipse cx={CX - 1} cy="332" rx="6" ry="20" fill="#fff" opacity="0.14" filter={`url(#blur3-${uid})`} />
            <ellipse cx={CX} cy="347" rx="10" ry="7" fill="#fff" opacity="0.16" filter={`url(#blur2-${uid})`} />
            <ellipse cx={CX} cy="366" rx="19" ry="5.5" fill={SK_D} opacity="0.3" filter={`url(#blur3-${uid})`} />
            <path d={`M${CX - 21} 348 Q${CX - 24} 361 ${CX - 12} 362 Q${CX - 6} 363 ${CX - 4} 358`} fill="none" stroke={SK_D} strokeWidth="2.6" strokeLinecap="round" opacity="0.7" />
            <path d={`M${CX + 21} 348 Q${CX + 24} 361 ${CX + 12} 362 Q${CX + 6} 363 ${CX + 4} 358`} fill="none" stroke={SK_D} strokeWidth="2.6" strokeLinecap="round" opacity="0.7" />
            <ellipse cx={CX - 9} cy="361" rx="4.2" ry="2.2" fill="#2a120c" opacity="0.5" />
            <ellipse cx={CX + 9} cy="361" rx="4.2" ry="2.2" fill="#2a120c" opacity="0.5" />
            {/* philtrum */}
            <path d={`M${CX - 6} 372 Q${CX - 5} ${mouthY - 16} ${CX - 7} ${mouthY - 14} M${CX + 6} 372 Q${CX + 5} ${mouthY - 16} ${CX + 7} ${mouthY - 14}`} fill="none" stroke={SK_D} strokeWidth="1.6" opacity="0.28" />
          </g>

          {/* beard */}
          {look.facialHair === 'beard' ? (
            <g>
              <path d={beardShape} fill={beardColor} filter={`url(#blur1-${uid})`} />
              <path d={beardShape} fill={`url(#jaw-${uid})`} opacity="0.5" />
              {strokesFor(
                [`M${CX - 70} 392 Q${CX - 66} 430 ${CX - 40} 460`, `M${CX + 70} 392 Q${CX + 66} 430 ${CX + 40} 460`, `M${CX - 20} 440 Q${CX} 462 ${CX + 20} 440`, `M${CX - 84} 340 Q${CX - 84} 390 ${CX - 60} 430`, `M${CX + 84} 340 Q${CX + 84} 390 ${CX + 60} 430`],
                '#9a9ea8',
                2,
                0.35
              )}
            </g>
          ) : null}

          {/* mouth */}
          <path d={lowerLip} fill={`url(#lipLo-${uid})`} />
          <path d={opening} fill="#3b1119" />
          <g clipPath={`url(#mouth-${uid})`}>
            <path d={`M${L.x + 7} ${cy - 2} H${R.x - 7} V${cy + 3 + gap * 0.16} Q${CX} ${cy + 6 + gap * 0.16} ${L.x + 7} ${cy + 3 + gap * 0.16} Z`} fill="#f1ebe2" opacity={open > 0.06 ? 1 : 0} />
            
            <ellipse cx={CX} cy={cy + 2 * gap * 0.62} rx={mw * 0.3} ry={4 + gap * 0.3} fill="#b94a5a" opacity={open > 0.15 ? 1 : 0} />
          </g>
          <path d={upperLip} fill={`url(#lipUp-${uid})`} />
          {/* soft highlight on the lower lip, and the shadow beneath it */}
          <ellipse cx={CX} cy={cy + 2 * gap * 0.5 + loThick * 0.9 + 2} rx={mw * 0.2} ry="2.4" fill="#fff" opacity="0.28" filter={`url(#blur2-${uid})`} />
          <ellipse cx={CX} cy={cy + 2 * gap * 0.5 + loThick * 2 + 8} rx={mw * 0.26} ry="4" fill={SK_D} opacity="0.2" filter={`url(#blur3-${uid})`} />
          <path d={`M${L.x} ${L.y} Q${CX} ${cy + 1.5 + lift * 0.4} ${R.x} ${R.y}`} fill="none" stroke={mixHex(lipDark, '#000', 0.3)} strokeWidth="1.9" strokeLinecap="round" opacity={open > 0.12 ? 0.25 : 0.9} />

          {look.facialHair === 'mustache' || look.facialHair === 'beard' ? (
            <path
              d={`M${CX} ${cy - upThick - 5} C${CX - 18} ${cy - upThick - 12} ${CX - 40} ${cy - upThick - 6} ${CX - mw / 2 - 12} ${cy + 4} C${CX - 40} ${cy - 2} ${CX - 18} ${cy - upThick + 2} ${CX} ${cy - upThick + 2} C${CX + 18} ${cy - upThick + 2} ${CX + 40} ${cy - 2} ${CX + mw / 2 + 12} ${cy + 4} C${CX + 40} ${cy - upThick - 6} ${CX + 18} ${cy - upThick - 12} ${CX} ${cy - upThick - 5} Z`}
              fill={beardColor}
              opacity={look.facialHair === 'beard' ? 1 : 0.95}
            />
          ) : null}

          {/* brows and eyes */}
          {brow(-1)}
          {brow(1)}
          {eye(-1)}
          {eye(1)}
          {glasses}
          {look.glasses ? (
            <>
              <path d={`M${CX - 8} ${eyeY - 8} Q${CX} ${eyeY - 14} ${CX + 8} ${eyeY - 8}`} fill="none" stroke={lensColor} strokeWidth="3" />
              <path d={`M${CX - ex - 38} ${eyeY - 8} L${CX - W - 6} ${eyeY - 12} M${CX + ex + 38} ${eyeY - 8} L${CX + W + 6} ${eyeY - 12}`} stroke={lensColor} strokeWidth="3" strokeLinecap="round" />
            </>
          ) : null}

          {/* hair on top */}
          {hairParts.front}
        </g>
      </g>
      </g>
    </svg>
  );
};
