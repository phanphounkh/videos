import React from 'react';
import { AbsoluteFill, Audio, Easing, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

/**
 * Sorya legal-assistant product demo ("The Unicorn Cake Disaster").
 * Everything is driven by a Plan (see build-plan.mjs): real screen recordings of the app,
 * the evidence images, camera moves, captions and sound cues, all on one frame timeline.
 */
export type Cam = { f: number; s: number; x: number; y: number };
export type Hl = { f: number; dur: number; x: number; y: number; w: number; h: number; color?: string };
export type Clip = {
  id: string;
  kind: 'image' | 'video' | 'card';
  from: number;
  dur: number;
  src?: string;
  srcStart?: number; // seconds into the source video
  rate?: number;
  cam?: Cam[];
  hl?: Hl[]; // image clips: highlight boxes, as fractions of the image
  variant?: string;
  lines?: string[];
  note?: string;
  badge?: string;
  fadeIn?: number;
  fadeOut?: number;
  shake?: boolean;
  bg?: string;
};
export type Cue = { f: number; src: string; vol?: number };
export type Cap = { f: number; dur: number; text: string; pos?: 'bottom' | 'top' | 'center'; big?: boolean };
export type Plan = { fps: number; total: number; lang: 'en' | 'km'; clips: Clip[]; sfx: Cue[]; vo: Cue[]; caps: Cap[] };

const GREEN = '#073f32';
const PAPER = '#fbf9f0';
const INK = '#2d3530';
const ease = Easing.bezier(0.16, 1, 0.3, 1);
const glide = Easing.bezier(0.45, 0, 0.2, 1);

const FONTS = `
@font-face{font-family:'SerifB';src:url(${staticFile('fonts/serif600.woff2')}) format('woff2');font-weight:600}
@font-face{font-family:'PlexB';src:url(${staticFile('fonts/plex600.woff2')}) format('woff2');font-weight:600}
@font-face{font-family:'PlexB';src:url(${staticFile('fonts/plex500.woff2')}) format('woff2');font-weight:500}
@font-face{font-family:'KhmerB';src:url(${staticFile('fonts/khmer700.woff2')}) format('woff2');font-weight:700}
@font-face{font-family:'KhmerB';src:url(${staticFile('fonts/khmer500.woff2')}) format('woff2');font-weight:500}
`;
const SANS = "'PlexB','KhmerB','Noto Sans Khmer','Noto Sans',sans-serif";
const SERIF = "'SerifB','Source Serif 4','Noto Serif Khmer','DejaVu Serif',serif";

/** Camera: scale `s` about the source point (x,y), eased between keyframes. */
const useCam = (cam: Cam[] | undefined, frame: number) => {
  if (!cam || cam.length === 0) return { s: 1, x: 960, y: 540 };
  const fs = cam.map((c) => c.f);
  const run = (k: 's' | 'x' | 'y') =>
    interpolate(frame, fs, cam.map((c) => c[k]), { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: glide });
  return { s: run('s'), x: run('x'), y: run('y') };
};
const camStyle = (c: { s: number; x: number; y: number }, W: number, H: number): React.CSSProperties => {
  const tx = Math.min(0, Math.max(W - W * c.s, W / 2 - c.x * c.s));
  const ty = Math.min(0, Math.max(H - H * c.s, H / 2 - c.y * c.s));
  return { position: 'absolute', left: 0, top: 0, width: W, height: H, transformOrigin: '0 0', transform: `translate(${tx}px,${ty}px) scale(${c.s})` };
};

const ImageClip: React.FC<{ clip: Clip }> = ({ clip }) => {
  const frame = useCurrentFrame();
  const { width: W, height: H } = useVideoConfig();
  const c = useCam(clip.cam, frame);
  const shake = clip.shake ? Math.sin(frame * 1.9) * Math.max(0, 1 - frame / 14) * 14 : 0;
  return (
    <AbsoluteFill style={{ background: clip.bg ?? 'radial-gradient(120% 120% at 30% 20%, #fff7e2 0%, #f1ead6 55%, #e6dcc2 100%)', overflow: 'hidden' }}>
      <div style={{ ...camStyle(c, W, H), transform: `${camStyle(c, W, H).transform} translateX(${shake}px)` }}>
        <div style={{ position: 'absolute', inset: 0, display: 'grid', placeItems: 'center' }}>
          <div style={{ position: 'relative', height: 940, borderRadius: 26, overflow: 'visible', boxShadow: '0 40px 90px rgba(45,53,48,.28), 0 6px 18px rgba(45,53,48,.18)' }}>
            <Img src={staticFile(clip.src!)} />
            {(clip.hl ?? []).map((h, i) => {
              const p = interpolate(frame - h.f, [0, 14], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease });
              const out = interpolate(frame - h.f, [h.dur - 8, h.dur], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
              const pulse = 1 + 0.015 * Math.sin((frame - h.f) / 4);
              return (
                <div key={i} style={{ position: 'absolute', left: `${h.x * 100}%`, top: `${h.y * 100}%`, width: `${h.w * 100}%`, height: `${h.h * 100}%`, borderRadius: 22, border: `6px solid ${h.color ?? '#e5484d'}`, background: `${h.color ?? '#e5484d'}22`, opacity: p * out, transform: `scale(${(0.94 + 0.06 * p) * pulse})`, boxShadow: `0 0 0 8px ${h.color ?? '#e5484d'}22` }} />
              );
            })}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
const Img: React.FC<{ src: string }> = ({ src }) => <img src={src} style={{ height: '100%', width: 'auto', display: 'block', borderRadius: 26 }} />;

const VideoClip: React.FC<{ clip: Clip }> = ({ clip }) => {
  const frame = useCurrentFrame();
  const { fps, width: W, height: H } = useVideoConfig();
  const c = useCam(clip.cam, frame);
  return (
    <AbsoluteFill style={{ background: PAPER, overflow: 'hidden' }}>
      <div style={camStyle(c, W, H)}>
        <OffthreadVideo src={staticFile(clip.src!)} startFrom={Math.round((clip.srcStart ?? 0) * fps)} playbackRate={clip.rate ?? 1} muted style={{ width: W, height: H }} />
      </div>
      {clip.badge ? <Badge text={clip.badge} /> : null}
    </AbsoluteFill>
  );
};
const Badge: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const a = interpolate(frame, [0, 8], [0, 1], { extrapolateRight: 'clamp' });
  return (
    <div style={{ position: 'absolute', right: 56, bottom: 56, opacity: a, display: 'flex', alignItems: 'center', gap: 12, background: 'rgba(7,63,50,.92)', color: '#fff', fontFamily: SANS, fontWeight: 600, fontSize: 30, padding: '12px 24px', borderRadius: 999, boxShadow: '0 10px 30px rgba(0,0,0,.25)' }}>
      <span style={{ width: 12, height: 12, borderRadius: 6, background: '#7ee0b4', opacity: 0.55 + 0.45 * Math.sin(frame / 3) }} />
      {text}
    </div>
  );
};

const Wordmark: React.FC<{ size: number; color?: string }> = ({ size, color = GREEN }) => (
  <span style={{ fontFamily: SERIF, fontWeight: 600, fontSize: size, color, letterSpacing: -size * 0.02, lineHeight: 1 }}>sorya</span>
);

const CardClip: React.FC<{ clip: Clip }> = ({ clip }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 14, stiffness: 120 } });
  const rise = interpolate(frame, [0, 20], [30, 0], { extrapolateRight: 'clamp', easing: ease });
  const op = interpolate(frame, [0, 14], [0, 1], { extrapolateRight: 'clamp' });
  const bg = clip.variant === 'skai' ? 'radial-gradient(100% 100% at 50% 40%, #0d5a47 0%, #073f32 60%, #052e25 100%)' : 'radial-gradient(120% 120% at 50% 35%, #fffdf4 0%, #f3eed9 70%, #e8e0c4 100%)';
  return (
    <AbsoluteFill style={{ background: bg, alignItems: 'center', justifyContent: 'center' }}>
      {clip.variant === 'logo' && (
        <div style={{ textAlign: 'center', opacity: op, transform: `translateY(${rise}px) scale(${0.9 + 0.1 * pop})` }}>
          <Wordmark size={210} />
          <div style={{ marginTop: 18, fontFamily: SANS, fontWeight: 600, fontSize: 40, letterSpacing: 18, color: '#5c6b5e', paddingLeft: 18 }}>AI</div>
        </div>
      )}
      {clip.variant === 'close' && (
        <div style={{ textAlign: 'center', opacity: op, transform: `translateY(${rise}px)`, maxWidth: 1560 }}>
          <div style={{ transform: `scale(${0.9 + 0.1 * pop})` }}>
            <Wordmark size={150} />
            <div style={{ marginTop: 10, fontFamily: SANS, fontWeight: 600, fontSize: 30, letterSpacing: 14, color: '#5c6b5e', paddingLeft: 14 }}>AI</div>
          </div>
          <div style={{ marginTop: 56, display: 'flex', flexDirection: 'column', gap: 18 }}>
            {(clip.lines ?? []).map((l, i) => {
              const a = interpolate(frame, [18 + i * 16, 34 + i * 16], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: ease });
              return (
                <div key={i} style={{ opacity: a, transform: `translateY(${(1 - a) * 22}px)`, fontFamily: i === 1 ? SERIF : SANS, fontWeight: i === 1 ? 600 : 500, fontSize: i === 1 ? 62 : 44, color: i === 1 ? GREEN : INK, lineHeight: 1.3 }}>
                  {l}
                </div>
              );
            })}
          </div>
          {clip.note ? <div style={{ marginTop: 54, fontFamily: SANS, fontWeight: 500, fontSize: 26, color: '#7d8c7f', opacity: interpolate(frame, [70, 90], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }) }}>{clip.note}</div> : null}
        </div>
      )}
      {clip.variant === 'skai' && (
        <div style={{ textAlign: 'center', opacity: op, transform: `translateY(${rise}px) scale(${0.9 + 0.1 * pop})`, color: '#fff' }}>
          <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 150, letterSpacing: 26, paddingLeft: 26 }}>SKAI</div>
          <div style={{ marginTop: 6, fontFamily: SANS, fontWeight: 500, fontSize: 38, letterSpacing: 22, paddingLeft: 22, color: '#9fd8c3' }}>TECHNOLOGY</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

const CapView: React.FC<{ cap: Cap; lang: 'en' | 'km' }> = ({ cap, lang }) => {
  const frame = useCurrentFrame();
  const inn = interpolate(frame, [0, 12], [0, 1], { extrapolateRight: 'clamp', easing: ease });
  const out = interpolate(frame, [cap.dur - 9, cap.dur], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const lines = cap.text.split('\n');
  const pos: React.CSSProperties = cap.pos === 'top' ? { top: 70 } : cap.pos === 'center' ? { top: '50%', transform: 'translateY(-50%)' } : { bottom: 78 };
  const fs = cap.big ? 70 : lang === 'km' ? 46 : 46;
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, display: 'flex', justifyContent: 'center', ...pos }}>
      <div style={{ opacity: inn * out, transform: `translateY(${(1 - inn) * 26}px)`, display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'center' }}>
        {lines.map((l, i) => (
          <div key={i} style={{ fontFamily: SANS, fontWeight: 600, fontSize: fs, lineHeight: 1.35, color: '#fff', background: 'rgba(7,63,50,.94)', padding: lang === 'km' ? '12px 40px 16px' : '10px 38px 14px', borderRadius: 18, boxShadow: '0 14px 40px rgba(0,0,0,.28)', transform: `translateY(${(1 - inn) * 10 * i}px)` }}>
            {l}
          </div>
        ))}
      </div>
    </div>
  );
};

export const LegalDemo: React.FC<{ plan: Plan }> = ({ plan }) => {
  return (
    <AbsoluteFill style={{ background: PAPER }}>
      <style>{FONTS}</style>
      {plan.clips.map((c) => (
        <Sequence key={c.id} from={c.from} durationInFrames={c.dur} layout="none">
          <FadeBox fadeIn={c.fadeIn ?? 0} fadeOut={c.fadeOut ?? 0} dur={c.dur}>
            {c.kind === 'image' ? <ImageClip clip={c} /> : c.kind === 'video' ? <VideoClip clip={c} /> : <CardClip clip={c} />}
          </FadeBox>
        </Sequence>
      ))}
      {plan.caps.map((cap, i) => (
        <Sequence key={'cap' + i} from={cap.f} durationInFrames={cap.dur} layout="none">
          <CapView cap={cap} lang={plan.lang} />
        </Sequence>
      ))}
      {plan.sfx.map((c, i) => (
        <Sequence key={'sfx' + i} from={Math.max(0, c.f)} layout="none">
          <Audio src={staticFile(c.src)} volume={c.vol ?? 1} />
        </Sequence>
      ))}
      {plan.vo.map((c, i) => (
        <Sequence key={'vo' + i} from={Math.max(0, c.f)} layout="none">
          <Audio src={staticFile(c.src)} volume={c.vol ?? 1} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

const FadeBox: React.FC<{ fadeIn: number; fadeOut: number; dur: number; children: React.ReactNode }> = ({ fadeIn, fadeOut, dur, children }) => {
  const frame = useCurrentFrame();
  const a = fadeIn ? interpolate(frame, [0, fadeIn], [0, 1], { extrapolateRight: 'clamp' }) : 1;
  const b = fadeOut ? interpolate(frame, [dur - fadeOut, dur], [1, 0], { extrapolateLeft: 'clamp' }) : 1;
  return <AbsoluteFill style={{ opacity: a * b }}>{children}</AbsoluteFill>;
};
