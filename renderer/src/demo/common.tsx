import React, { createContext, useContext, useMemo } from 'react';
import { AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame } from 'remotion';
import { fontFor } from '../story';
import type { Lang } from './copy';

export const FPS = 30;
export const ORANGE = '#ff7a1a';
export const AMBER = '#ffb340';
export const GRAD = 'linear-gradient(135deg,#ffb340,#ff7a1a)';
export const INK = '#0a0a10';
export const PANEL = '#14141d';
export const LINE = 'rgba(255,255,255,0.09)';
export const MUTED = '#8b8ba0';

export const ease = Easing.bezier(0.16, 1, 0.3, 1);
export const easeIn = Easing.bezier(0.7, 0, 0.84, 0);
export const glide = Easing.bezier(0.45, 0, 0.2, 1);

export const ramp = (f: number, a: number, b: number, easing: (t: number) => number = ease): number =>
  interpolate(f, [a, b], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing });

/** Spring with a slight overshoot, 0 before `delay`. */
export const pop = (f: number, delay = 0, damping = 10): number =>
  spring({ frame: f - delay, fps: FPS, config: { damping, stiffness: 180, mass: 0.7 } });

export const LangContext = createContext<Lang>('en');
export const useLang = (): Lang => useContext(LangContext);

/* ------------------------------------------------------------------ icons */

const ICONS: Record<string, string> = {
  wand: 'M5 19L15 9M14 4l1 2 2 1-2 1-1 2-1-2-2-1 2-1zM19 12l.7 1.3L21 14l-1.3.7L19 16l-.7-1.3L17 14l1.3-.7z',
  scissors: 'M6 8a3 3 0 100-6 3 3 0 000 6zM6 22a3 3 0 100-6 3 3 0 000 6zM8 7l12 11M8 17L20 6',
  undo: 'M9 14L4 9l5-5M4 9h10a6 6 0 010 12h-3',
  redo: 'M15 14l5-5-5-5M20 9H10a6 6 0 000 12h3',
  star: 'M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4 6.1 20.5l1.2-6.5L2.5 9.4l6.6-.9z',
  folder: 'M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z',
  trash: 'M4 7h16M10 11v6M14 11v6M6 7l1 12a2 2 0 002 2h6a2 2 0 002-2l1-12M9 7V4h6v3',
  check: 'M4 12.5l5 5L20 6.5',
  type: 'M5 6V4h14v2M12 4v16M9 20h6',
  music: 'M9 18V5l11-2v13M9 18a3 3 0 11-6 0 3 3 0 016 0zM20 16a3 3 0 11-6 0 3 3 0 016 0z',
  layers: 'M12 3l9 5-9 5-9-5zM3 13l9 5 9-5',
  image: 'M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4M9 9.5a1 1 0 100-.01',
  download: 'M12 4v11M7 11l5 5 5-5M5 20h14',
  sparkle: 'M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z',
  captions: 'M4 6h16v12H4zM8 11h3M13 11h3M8 14h6',
  sticker: 'M20 12a8 8 0 11-8-8h1v5a3 3 0 003 3zM8.5 10h.01M8 14.5c1 1.5 3 2 5 1.2',
  restore: 'M4 12a8 8 0 108-8M4 4v5h5',
  share: 'M18 8a3 3 0 100-6 3 3 0 000 6zM6 15a3 3 0 100-6 3 3 0 000 6zM18 22a3 3 0 100-6 3 3 0 000 6zM8.6 13.5l6.8 4M15.4 6.5l-6.8 4',
  play: 'M7 4l13 8-13 8z',
  plus: 'M12 5v14M5 12h14',
  link: 'M10 14a4 4 0 005.7 0l3-3a4 4 0 00-5.7-5.7l-1 1M14 10a4 4 0 00-5.7 0l-3 3a4 4 0 005.7 5.7l1-1'
};

export const Icon: React.FC<{ name: string; size?: number; color?: string; fill?: boolean; stroke?: number; style?: React.CSSProperties }> = ({
  name,
  size = 28,
  color = '#fff',
  fill = false,
  stroke = 2,
  style
}) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill ? color : 'none'} stroke={color} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={style}>
    <path d={ICONS[name]} />
  </svg>
);

/* --------------------------------------------------------------- sun mark */

export const SunMark: React.FC<{ size: number; rotate?: number }> = ({ size, rotate = 0 }) => (
  <svg width={size} height={size} viewBox="0 0 200 200" style={{ overflow: 'visible', filter: 'drop-shadow(0 0 30px rgba(255,122,26,.55))' }}>
    <defs>
      <linearGradient id="sunGrad" gradientUnits="userSpaceOnUse" x1="20" y1="20" x2="180" y2="180">
        <stop offset="0" stopColor={AMBER} />
        <stop offset="1" stopColor={ORANGE} />
      </linearGradient>
    </defs>
    <g transform={`rotate(${rotate} 100 100)`}>
      {Array.from({ length: 8 }, (_, i) => (
        <line key={i} x1="100" y1="12" x2="100" y2="34" stroke="url(#sunGrad)" strokeWidth="12" strokeLinecap="round" transform={`rotate(${i * 45} 100 100)`} />
      ))}
    </g>
    <circle cx="100" cy="100" r="58" fill="url(#sunGrad)" />
    <circle cx="80" cy="80" r="17" fill="#fff" opacity="0.28" />
  </svg>
);

/* ------------------------------------------------------------- background */

export const DemoBackground: React.FC = () => {
  const f = useCurrentFrame();
  const t = f / FPS;
  const dots = useMemo(
    () =>
      Array.from({ length: 46 }, (_, i) => ({
        x: random(`px${i}`) * 1920,
        y: random(`py${i}`) * 1080,
        r: 1.5 + random(`pr${i}`) * 3,
        speed: 8 + random(`ps${i}`) * 22,
        tw: random(`pt${i}`) * 6.28,
        warm: random(`pw${i}`) > 0.5
      })),
    []
  );
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 120% at 50% 0%, #14141d 0%, ${INK} 60%)`, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', width: 1100, height: 1100, borderRadius: '50%', left: 200 + Math.sin(t * 0.35) * 260, top: -520 + Math.cos(t * 0.28) * 120, background: 'radial-gradient(circle, rgba(255,122,26,.20), transparent 62%)' }} />
      <div style={{ position: 'absolute', width: 1000, height: 1000, borderRadius: '50%', left: 1000 + Math.cos(t * 0.3) * 240, top: 380 + Math.sin(t * 0.33) * 160, background: 'radial-gradient(circle, rgba(255,179,64,.12), transparent 62%)' }} />
      <div style={{ position: 'absolute', width: 900, height: 900, borderRadius: '50%', left: -300 + Math.sin(t * 0.25 + 2) * 200, top: 500 + Math.cos(t * 0.22) * 150, background: 'radial-gradient(circle, rgba(90,110,255,.12), transparent 62%)' }} />
      <div
        style={{
          position: 'absolute',
          inset: -80,
          backgroundImage: 'linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px)',
          backgroundSize: '80px 80px',
          backgroundPosition: `${(t * 6) % 80}px ${(t * 4) % 80}px`,
          maskImage: 'radial-gradient(70% 70% at 50% 45%, #000, transparent)'
        }}
      />
      {dots.map((d, i) => {
        const y = (((d.y - t * d.speed) % 1180) + 1180) % 1180 - 50;
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: d.x + Math.sin(t * 0.6 + d.tw) * 16,
              top: y,
              width: d.r * 2,
              height: d.r * 2,
              borderRadius: '50%',
              background: d.warm ? AMBER : '#fff',
              opacity: 0.12 + 0.14 * (0.5 + 0.5 * Math.sin(t * 1.5 + d.tw))
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};

/* ------------------------------------------------------------ scene frame */

export type Enter = 'none' | 'slide' | 'sweep' | 'iris';

/** Wraps a scene and animates its entrance (when it overlaps the previous scene) and exit. */
export const SceneFrame: React.FC<{ length: number; overlap: number; enter: Enter; exit: boolean; children: React.ReactNode }> = ({
  length,
  overlap,
  enter,
  exit,
  children
}) => {
  const f = useCurrentFrame();
  const inP = enter === 'none' ? 1 : ramp(f, 0, overlap + 6);
  const outP = exit ? ramp(f, length - overlap, length, easeIn) : 0;
  const style: React.CSSProperties = { position: 'absolute', inset: 0 };

  let transform = `translateX(${-outP * 90}px) scale(${1 - outP * 0.035})`;
  let opacity = 1 - outP;
  let filter = outP > 0 ? `blur(${outP * 10}px)` : undefined;
  let mask: string | undefined;
  let clip: string | undefined;

  if (enter === 'slide' && inP < 1) {
    transform = `translateX(${(1 - inP) * 140}px) scale(${0.96 + 0.04 * inP})`;
    opacity = Math.min(1, inP * 1.8);
    filter = `blur(${(1 - inP) * 12}px)`;
  } else if (enter === 'sweep' && inP < 1) {
    const edge = inP * 135;
    mask = `linear-gradient(100deg, #000 ${edge - 32}%, transparent ${edge}%)`;
  } else if (enter === 'iris' && inP < 1) {
    clip = `circle(${inP * 1250}px at 50% 50%)`;
    transform = `scale(${1.05 - inP * 0.05})`;
  }
  if (outP > 0 && inP < 1) opacity = 1;

  return (
    <div style={style}>
      <div style={{ ...style, transform, opacity, filter, clipPath: clip, WebkitMaskImage: mask, maskImage: mask }}>{children}</div>
      {enter === 'sweep' && inP < 1 ? (
        <div
          style={{
            position: 'absolute',
            top: -100,
            bottom: -100,
            width: 520,
            left: `${inP * 135 - 16}%`,
            transform: 'translateX(-60%) skewX(-16deg)',
            background: 'linear-gradient(90deg, transparent, rgba(255,150,40,.0) 10%, rgba(255,160,50,.75) 55%, rgba(255,230,170,.95) 62%, transparent)',
            filter: 'blur(14px)',
            opacity: 1 - ramp(inP, 0.7, 1, Easing.linear) * 0.8,
            mixBlendMode: 'screen'
          }}
        />
      ) : null}
      {enter === 'iris' && inP < 1 ? (
        <div
          style={{
            position: 'absolute',
            left: 960 - inP * 1250,
            top: 540 - inP * 1250,
            width: inP * 2500,
            height: inP * 2500,
            borderRadius: '50%',
            border: '6px solid rgba(255,160,50,.9)',
            boxShadow: '0 0 60px rgba(255,122,26,.8), inset 0 0 60px rgba(255,122,26,.5)',
            opacity: 1 - inP * 0.9
          }}
        />
      ) : null}
    </div>
  );
};

/* ------------------------------------------------------------------ text */

const segmentWords = (text: string, lang: Lang): string[] => {
  if (lang === 'en') return text.split(/\s+/).filter(Boolean);
  const Segmenter = (Intl as unknown as { Segmenter?: new (l: string, o: object) => { segment: (t: string) => Iterable<{ segment: string }> } }).Segmenter;
  if (!Segmenter) return [text];
  const units: string[] = [];
  for (const { segment } of new Segmenter('km', { granularity: 'word' }).segment(text)) {
    if (units.length > 0 && (/^[\u17D4-\u17DA\s.,!?:;]+$/.test(segment) || !/[ក-៝0-9A-Za-z]/.test(segment))) units[units.length - 1] += segment;
    else units.push(segment);
  }
  return units.filter((u) => u.trim());
};

/** Bottom caption: words reveal one by one while an orange highlight sweeps through each. */
export const KaraokeCaption: React.FC<{ text: string; start?: number; bottom?: number; size?: number }> = ({ text, start = 20, bottom = 44, size }) => {
  const f = useCurrentFrame();
  const lang = useLang();
  const km = lang === 'km';
  const words = useMemo(() => segmentWords(text, lang), [text, lang]);
  const step = km ? 6 : 8;
  const fontSize = size ?? (km ? 54 : 62);
  const box = pop(f, start - 8, 14);
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, bottom, display: 'flex', justifyContent: 'center', zIndex: 40 }}>
      <div
        style={{
          maxWidth: 1580,
          padding: km ? '10px 52px 14px' : '20px 52px 24px',
          borderRadius: 44,
          background: 'rgba(10,10,16,.72)',
          border: '1px solid rgba(255,255,255,.12)',
          boxShadow: '0 20px 60px rgba(0,0,0,.5), 0 0 0 1px rgba(255,122,26,.08)',
          textAlign: 'center',
          fontFamily: fontFor(lang),
          fontWeight: 800,
          fontSize,
          lineHeight: km ? 1.75 : 1.2,
          color: '#fff',
          opacity: Math.min(1, box * 1.5),
          transform: `translateY(${(1 - box) * 30}px) scale(${0.94 + 0.06 * box})`
        }}
      >
        {words.map((w, i) => {
          const rf = start + i * step;
          const a = ramp(f, rf, rf + 9);
          const sweep = ramp(f, rf + 1, rf + 11, Easing.out(Easing.quad));
          const fade = 1 - ramp(f, rf + step + 8, rf + step + 20, Easing.linear);
          return (
            <span
              key={i}
              style={{
                position: 'relative',
                display: 'inline-block',
                margin: km ? '0 0.05em' : '0 0.17em',
                opacity: a,
                transform: `translateY(${(1 - a) * 22}px) scale(${0.88 + 0.12 * a + (sweep < 1 ? 0.06 * Math.sin(sweep * Math.PI) : 0)})`,
                filter: a < 1 ? `blur(${(1 - a) * 6}px)` : undefined,
                whiteSpace: 'pre'
              }}
            >
              {w}
              <span
                style={{
                  position: 'absolute',
                  left: 0,
                  top: 0,
                  color: AMBER,
                  textShadow: '0 0 22px rgba(255,122,26,.7)',
                  opacity: fade,
                  clipPath: `inset(-10% ${(1 - sweep) * 100}% -10% 0)`
                }}
              >
                {w}
              </span>
            </span>
          );
        })}
      </div>
    </div>
  );
};

export const StepTitle: React.FC<{ n: number; text: string }> = ({ n, text }) => {
  const f = useCurrentFrame();
  const lang = useLang();
  const km = lang === 'km';
  const a = pop(f, 6, 13);
  const t = ramp(f, 10, 34);
  return (
    <div style={{ position: 'absolute', left: 96, top: 44, display: 'flex', alignItems: 'center', gap: 24, zIndex: 40, opacity: Math.min(1, a * 2), transform: `translateX(${(1 - a) * -70}px)` }}>
      <div style={{ width: 76, height: 76, borderRadius: 22, background: GRAD, display: 'grid', placeItems: 'center', fontFamily: fontFor('en'), fontWeight: 900, fontSize: 44, color: '#1a0e02', boxShadow: '0 10px 40px rgba(255,122,26,.45)', transform: `rotate(${(1 - a) * -25}deg)` }}>{n}</div>
      <div>
        <div style={{ fontFamily: fontFor(lang), fontWeight: 900, fontSize: km ? 56 : 62, lineHeight: km ? 1.5 : 1.1, color: '#fff', letterSpacing: km ? 0 : '-0.01em' }}>{text}</div>
        <div style={{ height: 5, borderRadius: 3, width: `${t * 100}%`, background: GRAD, marginTop: km ? 0 : 4 }} />
      </div>
    </div>
  );
};

/* ------------------------------------------------------------ UI pieces */

export const Win: React.FC<{ x: number; y: number; w: number; h: number; title?: string; children?: React.ReactNode; right?: React.ReactNode; style?: React.CSSProperties }> = ({
  x,
  y,
  w,
  h,
  title,
  children,
  right,
  style
}) => (
  <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: 30, background: PANEL, border: `1px solid ${LINE}`, boxShadow: '0 40px 90px rgba(0,0,0,.55), 0 0 80px rgba(255,122,26,.07)', overflow: 'hidden', fontFamily: fontFor('en'), ...style }}>
    <div style={{ height: 56, display: 'flex', alignItems: 'center', padding: '0 24px', gap: 10, borderBottom: `1px solid ${LINE}`, background: 'rgba(255,255,255,.025)' }}>
      {['#ff5f57', '#febc2e', '#28c840'].map((c) => (
        <div key={c} style={{ width: 15, height: 15, borderRadius: '50%', background: c }} />
      ))}
      {title ? <div style={{ marginLeft: 18, color: MUTED, fontSize: 21, fontWeight: 600 }}>{title}</div> : null}
      <div style={{ marginLeft: 'auto', display: 'flex', gap: 14, alignItems: 'center' }}>{right}</div>
    </div>
    {children}
  </div>
);

export type Waypoint = { f: number; x: number; y: number };

export const cursorPos = (f: number, pts: Waypoint[]): { x: number; y: number } => ({
  x: interpolate(f, pts.map((p) => p.f), pts.map((p) => p.x), { easing: glide, extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
  y: interpolate(f, pts.map((p) => p.f), pts.map((p) => p.y), { easing: glide, extrapolateLeft: 'clamp', extrapolateRight: 'clamp' })
});

export const Cursor: React.FC<{ pts: Waypoint[]; clicks?: number[]; hideAfter?: number }> = ({ pts, clicks = [], hideAfter }) => {
  const f = useCurrentFrame();
  const { x, y } = cursorPos(f, pts);
  const vis = ramp(f, pts[0].f, pts[0].f + 8, Easing.linear) * (hideAfter === undefined ? 1 : 1 - ramp(f, hideAfter, hideAfter + 10, Easing.linear));
  const press = clicks.reduce((m, c) => Math.max(m, f >= c && f < c + 8 ? Math.sin(((f - c) / 8) * Math.PI) : 0), 0);
  return (
    <>
      {clicks.map((c) => {
        const p = cursorPos(c, pts);
        const k = ramp(f, c, c + 20, Easing.out(Easing.cubic));
        if (f < c || k >= 1) return null;
        return <div key={c} style={{ position: 'absolute', left: p.x - 50, top: p.y - 50, width: 100, height: 100, borderRadius: '50%', border: `4px solid ${AMBER}`, background: 'rgba(255,179,64,.2)', transform: `scale(${0.2 + k * 0.9})`, opacity: 1 - k, zIndex: 60 }} />;
      })}
      <svg width="44" height="44" viewBox="0 0 32 36" style={{ position: 'absolute', left: x - 4, top: y - 3, zIndex: 61, opacity: vis, transform: `scale(${1 - press * 0.14})`, transformOrigin: '4px 3px', filter: 'drop-shadow(0 6px 10px rgba(0,0,0,.6))' }}>
        <path d="M4 3v26l7-6.5 5 11 5-2.2-5-10.6 9.5-.7z" fill="#fff" stroke="#14141d" strokeWidth="2.2" strokeLinejoin="round" />
      </svg>
    </>
  );
};

export const Confetti: React.FC<{ f: number; x: number; y: number; count?: number }> = ({ f, x, y, count = 70 }) => {
  const colors = [AMBER, ORANGE, '#fff', '#5eead4', '#a78bfa', '#fb7185'];
  if (f < 0) return null;
  return (
    <>
      {Array.from({ length: count }, (_, i) => {
        const ang = -Math.PI / 2 + (random(`ca${i}`) - 0.5) * 2.6;
        const sp = 9 + random(`cs${i}`) * 17;
        const px = x + Math.cos(ang) * sp * f * 0.8;
        const py = y + Math.sin(ang) * sp * f * 0.8 + 0.5 * 0.55 * f * f;
        const size = 10 + random(`cz${i}`) * 14;
        const life = 1 - ramp(f, 60, 90, Easing.linear);
        return <div key={i} style={{ position: 'absolute', left: px, top: py, width: size, height: size * (i % 3 === 0 ? 1 : 0.5), borderRadius: i % 4 === 0 ? '50%' : 3, background: colors[i % colors.length], transform: `rotate(${f * (6 + random(`cr${i}`) * 14)}deg)`, opacity: life, zIndex: 55 }} />;
      })}
    </>
  );
};

export const mouthAt = (f: number, talking: boolean): number => (talking ? Math.abs(Math.sin(f * 0.55)) * (0.55 + 0.45 * Math.abs(Math.sin(f * 0.13))) : 0);
