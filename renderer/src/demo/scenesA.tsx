import React from 'react';
import { Easing, interpolate, useCurrentFrame } from 'remotion';
import { Presenter } from '../components/Presenter';
import { fontFor, PHASE_THEME } from '../story';
import { AMBER, Cursor, GRAD, Icon, INK, KaraokeCaption, LINE, MUTED, ORANGE, PANEL, StepTitle, SunMark, Win, mouthAt, pop, ramp, useLang } from './common';
import { COPY } from './copy';

const UI = fontFor('en');

/* ------------------------------------------------------------------ intro */
export const IntroScene: React.FC = () => {
  const f = useCurrentFrame();
  const lang = useLang();
  const sun = pop(f, 4, 9);
  const spin = interpolate(ramp(f, 4, 50), [0, 1], [-200, 0]);
  const pulse = 1 + 0.035 * Math.sin(f * 0.18);
  const word = 'Sorya'.split('');
  return (
    <>
      {[8, 16, 24].map((d, i) => {
        const k = ramp(f, d, d + 40, Easing.out(Easing.cubic));
        return <div key={d} style={{ position: 'absolute', left: 960 - 130 - k * (300 + i * 80), top: 360 - 130 - k * (300 + i * 80) + 0, width: 260 + k * (600 + i * 160), height: 260 + k * (600 + i * 160), borderRadius: '50%', border: `${6 - i}px solid ${i === 1 ? AMBER : ORANGE}`, opacity: (1 - k) * 0.8 }} />;
      })}
      <div style={{ position: 'absolute', left: 960 - 130, top: 360 - 130, transform: `scale(${sun * pulse}) rotate(${spin}deg)` }}>
        <SunMark size={260} rotate={f * 0.6} />
      </div>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 505, display: 'flex', justifyContent: 'center', fontFamily: UI, fontWeight: 900, fontSize: 168, letterSpacing: '-0.03em', lineHeight: 1.25 }}>
        {word.map((ch, i) => {
          const a = ramp(f, 26 + i * 3, 52 + i * 3);
          return (
            <span key={i} style={{ display: 'inline-block', opacity: a, transform: `translateY(${(1 - a) * 80}px)`, backgroundImage: 'linear-gradient(135deg,#fff 20%,#ffd9a8)', WebkitBackgroundClip: 'text', color: 'transparent' }}>
              {ch}
            </span>
          );
        })}
      </div>
      <KaraokeCaption text={COPY[lang].captions[0]} start={52} bottom={150} />
    </>
  );
};

/* --------------------------------------------------------------- describe */
const WX = 340;
const WY = 160;
const CHIPS: [string, number][] = [['Story', 128], ['Product demo', 224], ['Social post', 196], ['Creator', 144], ['Explainer', 170]];
const PROMPT = 'A 30-second product demo for my coffee app';

export const DescribeScene: React.FC = () => {
  const f = useCurrentFrame();
  const lang = useLang();
  const t = COPY[lang];
  const win = pop(f, 4, 14);
  const typed = Math.floor(ramp(f, 34, 104, Easing.linear) * PROMPT.length);
  const caret = f < 110 ? f % 16 < 10 : f % 30 < 16 && f < 150;
  const selected = f >= 150;
  const clicked = f >= 206;
  const chipX: number[] = [];
  CHIPS.reduce((x, [, w], i) => ((chipX[i] = x), x + w + 16), 48);
  const btn = pop(f, 100, 12);
  const press = f >= 206 && f < 214 ? 0.94 : 1;
  const glow = !clicked ? 0.5 + 0.5 * Math.sin(f * 0.25) : 0;
  return (
    <>
      <StepTitle n={1} text={t.titles[0]} />
      <div style={{ opacity: Math.min(1, win * 1.5), transform: `translateY(${(1 - win) * 120}px) scale(${0.92 + 0.08 * win})` }}>
        <Win x={WX} y={WY} w={1240} h={600} title="Sorya  /  New video">
          <div style={{ position: 'relative' }}>
            <div style={{ position: 'absolute', left: 48, top: 26, fontSize: 24, color: MUTED, fontWeight: 600 }}>What is your video about?</div>
            <div style={{ position: 'absolute', left: 48, top: 68, width: 1144, height: 150, borderRadius: 22, background: INK, border: `2px solid ${f > 30 && !clicked ? 'rgba(255,179,64,.7)' : LINE}`, boxShadow: f > 30 ? '0 0 40px rgba(255,122,26,.18)' : undefined, padding: '30px 34px', fontSize: 40, fontWeight: 600, color: '#fff', fontFamily: UI }}>
              {PROMPT.slice(0, typed)}
              <span style={{ display: 'inline-block', width: 4, height: 44, marginLeft: 3, verticalAlign: -8, background: AMBER, opacity: caret ? 1 : 0 }} />
              {typed === 0 && f < 34 ? <span style={{ color: '#55556a' }}>Describe your idea...</span> : null}
            </div>
            <div style={{ position: 'absolute', left: 48, top: 244, fontSize: 24, color: MUTED, fontWeight: 600 }}>Kind of video</div>
            {CHIPS.map(([label, w], i) => {
              const p = pop(f, 110 + i * 4);
              const sel = selected && i === 1;
              const rip = i === 1 ? ramp(f, 148, 172, Easing.out(Easing.cubic)) : 1;
              return (
                <div key={label} style={{ position: 'absolute', left: chipX[i], top: 286, width: w, height: 58, opacity: Math.min(1, p * 2), transform: `scale(${0.6 + 0.4 * p}) translateY(${(1 - p) * 20}px)` }}>
                  {i === 1 && f >= 148 && rip < 1 ? <div style={{ position: 'absolute', inset: -2, borderRadius: 30, border: `3px solid ${AMBER}`, transform: `scale(${1 + rip * 0.45})`, opacity: 1 - rip }} /> : null}
                  <div style={{ width: '100%', height: '100%', borderRadius: 29, display: 'grid', placeItems: 'center', fontSize: 25, fontWeight: 700, background: sel ? GRAD : 'rgba(255,255,255,.06)', color: sel ? '#1a0e02' : '#d6d6e4', border: sel ? 'none' : `1px solid ${LINE}`, boxShadow: sel ? '0 8px 30px rgba(255,122,26,.45)' : undefined, transform: sel ? `scale(${1 + 0.08 * Math.sin(ramp(f, 148, 162) * Math.PI)})` : undefined }}>{label}</div>
                </div>
              );
            })}
            <div style={{ position: 'absolute', left: 48, top: 410, display: 'flex', gap: 22, color: MUTED, fontSize: 23, fontWeight: 600, opacity: ramp(f, 130, 150) }}>
              {['Script', 'Voice', 'Captions'].map((s) => (
                <span key={s} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Icon name="check" size={22} color="#5eead4" /> {s}
                </span>
              ))}
            </div>
            <div style={{ position: 'absolute', left: 912, top: 392, width: 280, height: 70, borderRadius: 22, background: GRAD, color: '#1a0e02', fontSize: 30, fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, opacity: Math.min(1, btn * 2), transform: `scale(${(0.7 + 0.3 * btn) * press * (1 + glow * 0.025)})`, boxShadow: `0 10px 40px rgba(255,122,26,${0.4 + glow * 0.4})` }}>
              {clicked ? (
                <>
                  <svg width="30" height="30" viewBox="0 0 30 30" style={{ transform: `rotate(${f * 14}deg)` }}>
                    <circle cx="15" cy="15" r="11" fill="none" stroke="rgba(26,14,2,.25)" strokeWidth="4" />
                    <path d="M15 4a11 11 0 0111 11" fill="none" stroke="#1a0e02" strokeWidth="4" strokeLinecap="round" />
                  </svg>
                  Generating
                </>
              ) : (
                <>
                  <Icon name="wand" size={32} color="#1a0e02" stroke={2.4} /> Generate
                </>
              )}
            </div>
          </div>
        </Win>
      </div>
      <Cursor
        pts={[{ f: 100, x: 1560, y: 900 }, { f: 142, x: WX + 48 + 192 + 112, y: WY + 56 + 286 + 29 }, { f: 152, x: WX + 48 + 192 + 112, y: WY + 56 + 286 + 29 }, { f: 204, x: WX + 912 + 140, y: WY + 56 + 392 + 35 }]}
        clicks={[148, 206]}
        hideAfter={236}
      />
      <KaraokeCaption text={t.captions[1]} start={24} />
    </>
  );
};

/* --------------------------------------------------------------- generate */
const LINES = ['Hook: meet your new coffee habit', 'Show the app in ten seconds', 'Highlight the best feature', 'Real customers, real love', 'Download it today'];
const LABELS = ['Hook', 'Demo', 'Feature', 'Proof', 'Call'];
const TINTS = [['#ffb340', '#ff7a1a'], ['#60a5fa', '#3b5bdb'], ['#5eead4', '#0d9488'], ['#c4b5fd', '#7c3aed'], ['#fda4af', '#e11d48']];

export const GenerateScene: React.FC = () => {
  const f = useCurrentFrame();
  const lang = useLang();
  const t = COPY[lang];
  const prog = ramp(f, 14, 122, Easing.inOut(Easing.cubic));
  const done = f >= 124;
  const host = pop(f, 30, 12);
  const talking = f > 50 && f < 235;
  const phase = f < 130 ? 'hook' : 'payoff';
  const sticker = pop(f, 150, 8);
  const R = 30;
  return (
    <>
      <StepTitle n={2} text={t.titles[1]} />
      {/* progress header */}
      <div style={{ position: 'absolute', left: 140, top: 168, display: 'flex', alignItems: 'center', gap: 22, fontFamily: UI, opacity: ramp(f, 4, 18) }}>
        <svg width="72" height="72" viewBox="0 0 72 72">
          <circle cx="36" cy="36" r={R} fill="none" stroke="rgba(255,255,255,.1)" strokeWidth="8" />
          <circle cx="36" cy="36" r={R} fill="none" stroke="url(#ringG)" strokeWidth="8" strokeLinecap="round" strokeDasharray={2 * Math.PI * R} strokeDashoffset={2 * Math.PI * R * (1 - prog)} transform="rotate(-90 36 36)" />
          <defs><linearGradient id="ringG"><stop offset="0" stopColor={AMBER} /><stop offset="1" stopColor={ORANGE} /></linearGradient></defs>
          {done ? <path d="M24 37l8 8 16-17" fill="none" stroke="#5eead4" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" /> : null}
        </svg>
        <div>
          <div style={{ fontSize: 36, fontWeight: 800, color: '#fff' }}>{done ? 'Script and scenes ready' : 'Writing your script...'}</div>
          <div style={{ fontSize: 22, fontWeight: 600, color: MUTED }}>{Math.round(prog * 100)}%  -  5 scenes</div>
        </div>
      </div>
      {/* lines flying in, then settling into scene cards */}
      {LINES.map((line, i) => {
        const appear = pop(f, 22 + i * 12, 12);
        const m = ramp(f, 128 + i * 6, 158 + i * 6);
        const x0 = 140, y0 = 262 + i * 70, w0 = 1060, h0 = 58;
        const x1 = 140 + i * 232, y1 = 590, w1 = 212, h1 = 170;
        const x = x0 + (x1 - x0) * m + (1 - appear) * 500;
        const y = y0 + (y1 - y0) * m;
        const w = w0 + (w1 - w0) * m;
        const h = h0 + (h1 - h0) * m;
        const [c1, c2] = TINTS[i];
        const text1 = 1 - ramp(m, 0, 0.4, Easing.linear);
        const text2 = ramp(m, 0.6, 1, Easing.linear);
        return (
          <div key={i} style={{ position: 'absolute', left: x, top: y, width: w, height: h, opacity: Math.min(1, appear * 2), borderRadius: 18 + m * 6, overflow: 'hidden', border: `1px solid ${LINE}`, background: `linear-gradient(135deg, ${m > 0 ? c1 + 'dd' : PANEL}, ${m > 0 ? c2 + 'cc' : PANEL})`, backgroundColor: PANEL, boxShadow: m > 0.5 ? `0 14px 40px ${c2}55` : '0 8px 24px rgba(0,0,0,.4)', fontFamily: UI, transform: `rotate(${(1 - appear) * 6}deg)` }}>
            <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(135deg, ${c1}, ${c2})`, opacity: ramp(m, 0, 0.7, Easing.linear) }} />
            <div style={{ position: 'absolute', left: 16, top: h0 / 2 - 17, width: 34, height: 34, borderRadius: 11, background: m > 0.2 ? 'rgba(10,10,16,.35)' : GRAD, color: m > 0.2 ? '#fff' : '#1a0e02', fontWeight: 900, fontSize: 21, display: 'grid', placeItems: 'center', transform: `translate(${m * (w1 / 2 - 33)}px, ${m * (h1 / 2 - h0 / 2 - 14)}px) scale(${1 + m * 0.7})` }}>{i + 1}</div>
            <div style={{ position: 'absolute', left: 66, top: 0, height: h0, display: 'flex', alignItems: 'center', fontSize: 28, fontWeight: 600, color: '#e8e8f2', whiteSpace: 'nowrap', opacity: text1 }}>{line}</div>
            <div style={{ position: 'absolute', left: 0, right: 0, bottom: 18, textAlign: 'center', fontSize: 28, fontWeight: 800, color: '#1a0e02', opacity: text2 }}>{LABELS[i]}</div>
          </div>
        );
      })}
      {/* host */}
      <div style={{ position: 'absolute', left: 1320, top: 190, width: 480, height: 570, borderRadius: 38, border: `1px solid ${LINE}`, background: `radial-gradient(90% 70% at 50% 100%, ${PHASE_THEME[phase].glow}55, ${PANEL} 70%)`, opacity: Math.min(1, host * 2), transform: `translateY(${(1 - host) * 140}px) scale(${0.85 + 0.15 * host})`, boxShadow: '0 30px 80px rgba(0,0,0,.5)' }}>
        <div style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, clipPath: 'inset(-120px -150px 0px -150px)' }}><div style={{ position: 'absolute', left: 50, top: 89, width: 380, height: 481 }}>
          <Presenter frame={Math.max(0, f - 32)} fps={30} mouthOpen={mouthAt(f, talking)} loudness={mouthAt(f, talking) * 0.9} talking={talking} phase={phase} theme={PHASE_THEME[phase]} cueFrame={150 - 32} cueSide="left" celebrateFrom={null} />
        </div></div>
      </div>
      <div style={{ position: 'absolute', left: 960, top: 196, padding: '18px 30px', borderRadius: 26, background: GRAD, color: '#1a0e02', fontFamily: UI, fontSize: 32, fontWeight: 900, lineHeight: 1.2, boxShadow: '0 16px 50px rgba(255,122,26,.5)', opacity: Math.min(1, sticker * 2), transform: `scale(${sticker}) rotate(${-4 + (1 - sticker) * -12}deg)`, transformOrigin: '100% 60%', zIndex: 20 }}>
        Script. Scenes. Captions.
        <div style={{ position: 'absolute', right: -14, top: 38, width: 28, height: 28, background: ORANGE, transform: 'rotate(45deg)', borderRadius: 6, zIndex: -1 }} />
      </div>
    </>
  );
};
