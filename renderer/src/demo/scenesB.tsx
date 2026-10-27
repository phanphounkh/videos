import React from 'react';
import { Easing, interpolate, useCurrentFrame } from 'remotion';
import { Presenter } from '../components/Presenter';
import { fontFor, PHASE_THEME } from '../story';
import { AMBER, Confetti, Cursor, GRAD, Icon, INK, KaraokeCaption, LINE, MUTED, ORANGE, PANEL, StepTitle, SunMark, Win, cursorPos, glide, mouthAt, pop, ramp, useLang } from './common';
import { COPY } from './copy';

const UI = fontFor('en');
const TINTS = [['#ffb340', '#ff7a1a'], ['#60a5fa', '#3b5bdb'], ['#5eead4', '#0d9488'], ['#c4b5fd', '#7c3aed'], ['#fda4af', '#e11d48'], ['#fde68a', '#d97706']];

/* ------------------------------------------------------------------- edit */
const EX = 120;
const EY = 150;
const EW = 1680;
const CLIPS = [300, 330, 310, 350, 270];
const CLIP_COL = [TINTS[0], TINTS[1], TINTS[2], TINTS[3], TINTS[4]];

export const EditScene: React.FC = () => {
  const f = useCurrentFrame();
  const lang = useLang();
  const t = COPY[lang];
  const win = pop(f, 2, 14);
  const trim = ramp(f, 205, 240, glide);
  const widths = CLIPS.map((w, i) => (i === 1 ? w - 80 * trim : w));
  const lefts: number[] = [];
  widths.reduce((x, w, i) => ((lefts[i] = x), x + w + 6), 40);
  const edge0 = 40 + CLIPS[0] + 6 + CLIPS[1];
  const sticker = pop(f, 130, 8);
  const play = ramp(f, 70, 232, Easing.inOut(Easing.quad));
  const tool = f >= 112 ? 1 : 0;
  const slider = 0.3 + 0.4 * ramp(f, 140, 190);
  const flash = (c: number) => (f >= c && f < c + 16 ? Math.sin(((f - c) / 16) * Math.PI) : 0);
  const undo = flash(270);
  const redo = flash(284);
  const talking = f > 40 && f < 290;
  return (
    <>
      <StepTitle n={3} text={t.titles[2]} />
      <div style={{ opacity: Math.min(1, win * 1.5), transform: `translateY(${(1 - win) * 100}px) scale(${0.94 + 0.06 * win})` }}>
        <Win
          x={EX}
          y={EY}
          w={EW}
          h={620}
          title="Coffee app demo"
          right={
            <>
              <div style={{ width: 44, height: 44, borderRadius: 14, display: 'grid', placeItems: 'center', background: undo ? 'rgba(255,179,64,.35)' : 'rgba(255,255,255,.06)', transform: `scale(${1 + undo * 0.3})`, boxShadow: undo ? '0 0 30px rgba(255,122,26,.8)' : undefined }}><Icon name="undo" size={24} color={undo ? AMBER : '#c8c8d8'} /></div>
              <div style={{ width: 44, height: 44, borderRadius: 14, display: 'grid', placeItems: 'center', background: redo ? 'rgba(255,179,64,.35)' : 'rgba(255,255,255,.06)', transform: `scale(${1 + redo * 0.3})`, boxShadow: redo ? '0 0 30px rgba(255,122,26,.8)' : undefined }}><Icon name="redo" size={24} color={redo ? AMBER : '#c8c8d8'} /></div>
              <div style={{ padding: '10px 22px', borderRadius: 14, background: GRAD, color: '#1a0e02', fontWeight: 800, fontSize: 22 }}>Export</div>
            </>
          }
        >
          <div style={{ position: 'relative' }}>
            {/* rail */}
            <div style={{ position: 'absolute', left: 0, top: 0, width: 72, height: 372, borderRight: `1px solid ${LINE}` }}>
              {['image', 'type', 'sticker', 'music', 'captions'].map((n, i) => {
                const p = pop(f, 10 + i * 4, 12);
                const act = (i === 1 && tool) || (i === 0 && !tool);
                return (
                  <div key={n} style={{ position: 'absolute', left: 12, top: 22 + i * 66, width: 48, height: 48, borderRadius: 15, display: 'grid', placeItems: 'center', background: act ? 'rgba(255,179,64,.18)' : 'transparent', border: act ? '1px solid rgba(255,179,64,.5)' : '1px solid transparent', transform: `scale(${p * (act && f >= 112 && f < 124 ? 1.18 : 1)})` }}>
                    <Icon name={n} size={26} color={act ? AMBER : MUTED} />
                  </div>
                );
              })}
            </div>
            {/* media bin */}
            {[0, 1, 2].map((i) => {
              const p = pop(f, 16 + i * 6, 12);
              return (
                <div key={i} style={{ position: 'absolute', left: 100, top: 22 + i * 116, width: 280, height: 100, borderRadius: 16, opacity: Math.min(1, p * 2), transform: `translateX(${(1 - p) * -60}px)`, background: `linear-gradient(135deg, ${TINTS[[1, 2, 3][i]][0]}, ${TINTS[[1, 2, 3][i]][1]})`, border: `1px solid ${LINE}`, overflow: 'hidden' }}>
                  <div style={{ position: 'absolute', left: 14, bottom: 10, fontFamily: UI, fontWeight: 800, fontSize: 20, color: 'rgba(10,10,16,.75)' }}>{['clip-01.mp4', 'photo.jpg', 'logo.png'][i]}</div>
                  <Icon name={['play', 'image', 'sparkle'][i]} size={30} color="rgba(10,10,16,.55)" style={{ position: 'absolute', right: 14, top: 12 }} />
                </div>
              );
            })}
            {/* preview */}
            <div style={{ position: 'absolute', left: 440, top: 19, width: 592, height: 333, borderRadius: 18, overflow: 'hidden', background: `radial-gradient(90% 80% at 50% 100%, ${PHASE_THEME.hook.glow}66, #1a1020 75%)`, border: `1px solid ${LINE}`, opacity: ramp(f, 6, 22) }}>
              <div style={{ position: 'absolute', left: 146, top: 8, width: 300, height: 380 }}>
                <Presenter frame={f} fps={30} mouthOpen={mouthAt(f, talking)} loudness={mouthAt(f, talking) * 0.8} talking={talking} phase="hook" theme={PHASE_THEME.hook} cueFrame={null} cueSide="left" celebrateFrom={null} />
              </div>
              <div style={{ position: 'absolute', left: 28, top: 26, padding: '8px 20px', borderRadius: 14, background: GRAD, color: '#1a0e02', fontFamily: UI, fontSize: 30, fontWeight: 900, transform: `scale(${sticker}) rotate(${-6 + (1 - sticker) * -20}deg)`, opacity: Math.min(1, sticker * 2), boxShadow: '0 8px 24px rgba(255,122,26,.5)', outline: sticker > 0.9 ? '2px dashed rgba(255,255,255,.8)' : undefined, outlineOffset: 6 }}>New: Cold Brew</div>
              <div style={{ position: 'absolute', left: 0, right: 0, bottom: 14, textAlign: 'center', fontFamily: UI, fontSize: 24, fontWeight: 900, color: '#fff', textShadow: '0 2px 8px #000' }}>
                {['Meet', 'your', 'new', 'coffee', 'habit'].map((w, i) => (
                  <span key={w} style={{ margin: '0 5px', color: Math.floor(f / 9) % 5 === i ? AMBER : '#fff' }}>{w}</span>
                ))}
              </div>
            </div>
            {/* properties */}
            <div style={{ position: 'absolute', left: 1100, top: 0, width: 580, height: 372, borderLeft: `1px solid ${LINE}`, padding: '24px 28px', opacity: ramp(f, 18, 36), fontFamily: UI }}>
              <div style={{ color: '#fff', fontSize: 24, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 10 }}><Icon name={tool ? 'type' : 'layers'} size={24} color={AMBER} /> {tool ? 'Text' : 'Scene 1'}</div>
              <div style={{ color: MUTED, fontSize: 18, fontWeight: 600, marginTop: 22 }}>Size</div>
              <div style={{ position: 'relative', height: 8, borderRadius: 4, background: 'rgba(255,255,255,.1)', marginTop: 12 }}>
                <div style={{ width: `${slider * 100}%`, height: '100%', borderRadius: 4, background: GRAD }} />
                <div style={{ position: 'absolute', left: `${slider * 100}%`, top: -8, width: 24, height: 24, marginLeft: -12, borderRadius: '50%', background: '#fff', boxShadow: '0 2px 10px rgba(0,0,0,.5)' }} />
              </div>
              <div style={{ color: MUTED, fontSize: 18, fontWeight: 600, marginTop: 26 }}>Colour</div>
              <div style={{ display: 'flex', gap: 14, marginTop: 12 }}>
                {['#ffb340', '#ffffff', '#5eead4', '#a78bfa', '#fb7185'].map((c, i) => (
                  <div key={c} style={{ width: 34, height: 34, borderRadius: '50%', background: c, outline: i === 0 && f > 150 ? `3px solid #fff` : undefined, outlineOffset: 3, transform: `scale(${pop(f, 40 + i * 4)})` }} />
                ))}
              </div>
              <div style={{ color: MUTED, fontSize: 18, fontWeight: 600, marginTop: 26 }}>Animation</div>
              <div style={{ display: 'flex', gap: 10, marginTop: 12 }}>
                {['Pop', 'Fade', 'Slide'].map((s, i) => (
                  <div key={s} style={{ padding: '8px 18px', borderRadius: 20, fontSize: 20, fontWeight: 700, background: i === 0 && f > 135 ? GRAD : 'rgba(255,255,255,.07)', color: i === 0 && f > 135 ? '#1a0e02' : '#cfcfe0' }}>{s}</div>
                ))}
              </div>
            </div>
            {/* timeline */}
            <div style={{ position: 'absolute', left: 0, top: 372, width: EW, height: 192, borderTop: `1px solid ${LINE}`, background: 'rgba(0,0,0,.18)', opacity: ramp(f, 14, 30) }}>
              {Array.from({ length: 17 }, (_, i) => (
                <div key={i} style={{ position: 'absolute', left: 40 + i * 100, top: 6, color: '#55556a', fontFamily: UI, fontSize: 15, fontWeight: 600 }}>
                  <div style={{ width: 2, height: 8, background: '#3a3a4c', marginBottom: 2 }} />0:{String(i * 2).padStart(2, '0')}
                </div>
              ))}
              {/* video clips */}
              {widths.map((w, i) => {
                const p = ramp(f, 30 + i * 7, 56 + i * 7);
                return (
                  <div key={i} style={{ position: 'absolute', left: lefts[i] + (1 - p) * 260, top: 44, width: w, height: 50, borderRadius: 10, opacity: p, background: `linear-gradient(135deg, ${CLIP_COL[i][0]}, ${CLIP_COL[i][1]})`, boxShadow: i === 1 && f > 190 && f < 250 ? '0 0 0 3px #fff, 0 0 30px rgba(255,255,255,.4)' : undefined, overflow: 'hidden' }}>
                    <div style={{ padding: '12px 14px', fontFamily: UI, fontWeight: 800, fontSize: 20, color: 'rgba(10,10,16,.75)' }}>Scene {i + 1}</div>
                    {i === 1 ? <div style={{ position: 'absolute', right: 0, top: 0, bottom: 0, width: 10, background: 'rgba(255,255,255,.85)' }} /> : null}
                  </div>
                );
              })}
              {/* waveform */}
              <div style={{ position: 'absolute', left: 40, top: 102, width: 1560, height: 40, borderRadius: 10, background: 'rgba(94,234,212,.08)', overflow: 'hidden', display: 'flex', alignItems: 'center', gap: 3 }}>
                {Array.from({ length: 200 }, (_, i) => {
                  const h = 6 + 28 * Math.abs(Math.sin(i * 0.37) * Math.cos(i * 0.11 + 1)) ** 0.8;
                  const s = ramp(f, 56 + i * 0.3, 74 + i * 0.3);
                  return <div key={i} style={{ width: 5, flex: '0 0 5px', height: h * s, borderRadius: 3, background: '#5eead4', opacity: 0.8 }} />;
                })}
              </div>
              {/* captions row */}
              {[0, 1, 2, 3, 4, 5, 6, 7].map((i) => {
                const w = 110 + ((i * 53) % 90);
                const x = 40 + i * 198;
                const p = ramp(f, 80 + i * 6, 100 + i * 6);
                return <div key={i} style={{ position: 'absolute', left: x, top: 150, width: w * p, height: 28, borderRadius: 9, background: 'rgba(167,139,250,.55)', border: '1px solid rgba(167,139,250,.9)', opacity: p }} />;
              })}
              {/* playhead */}
              <div style={{ position: 'absolute', left: 40 + play * 900, top: 0, width: 3, height: 192, background: '#fff', boxShadow: '0 0 12px rgba(255,255,255,.7)' }}>
                <div style={{ position: 'absolute', left: -9, top: -2, width: 21, height: 20, borderRadius: '5px 5px 10px 10px', background: ORANGE }} />
              </div>
            </div>
          </div>
        </Win>
      </div>
      <Cursor
        pts={[
          { f: 70, x: 1400, y: 900 },
          { f: 106, x: EX + 36, y: EY + 56 + 22 + 66 + 24 },
          { f: 124, x: EX + 36, y: EY + 56 + 22 + 66 + 24 },
          { f: 192, x: EX + edge0, y: EY + 56 + 372 + 69 },
          { f: 205, x: EX + edge0, y: EY + 56 + 372 + 69 },
          { f: 240, x: EX + edge0 - 80, y: EY + 56 + 372 + 69 },
          { f: 264, x: EX + EW - 200, y: EY + 28 },
          { f: 278, x: EX + EW - 200, y: EY + 28 },
          { f: 288, x: EX + EW - 140, y: EY + 28 }
        ]}
        clicks={[112, 270, 284]}
        hideAfter={300}
      />
      <KaraokeCaption text={t.captions[3]} start={26} />
    </>
  );
};

/* --------------------------------------------------------------- organise */
const FOLDERS = [['Coffee Shop', '12'], ['Social clips', '8'], ['Tutorials', '5']];
const PROJECTS = ['Summer promo', 'Coffee app demo', 'Launch teaser'];
const TEMPLATES = ['Product launch', 'Daily tips', 'Story time', 'Quick promo', 'Explainer', 'Recipe', 'Travel log', 'Top 5 list'];

export const OrganiseScene: React.FC = () => {
  const f = useCurrentFrame();
  const lang = useLang();
  const t = COPY[lang];
  const star = f >= 52;
  const starPop = pop(f, 52, 6);
  const grab = ramp(f, 72, 80);
  const move = ramp(f, 80, 112, glide);
  const cx = 635 + (295 - 635) * move;
  const cy = 435 + (240 - 435) * move;
  const scale = (1 + grab * 0.05) * (1 - move * 0.55);
  const gone = ramp(f, 106, 116);
  const folderBump = f >= 112 ? 1 + 0.08 * Math.sin(ramp(f, 112, 126) * Math.PI) : 1;
  const restored = f >= 146;
  const tx = 150 - (f - 100) * 1.1;
  const tplIn = ramp(f, 100, 150);
  return (
    <>
      <StepTitle n={4} text={t.titles[3]} />
      {FOLDERS.map(([name, n], i) => {
        const p = pop(f, 8 + i * 5, 12);
        const [c1, c2] = TINTS[[0, 3, 2][i]];
        const bump = i === 0 ? folderBump : 1;
        return (
          <div key={name} style={{ position: 'absolute', left: 140 + i * 340, top: 170, width: 310, height: 150, opacity: Math.min(1, p * 2), transform: `translateY(${(1 - p) * 60}px) scale(${(0.8 + 0.2 * p) * bump})`, fontFamily: UI }}>
            <div style={{ position: 'absolute', left: 0, top: 0, width: 120, height: 34, borderRadius: '16px 16px 0 0', background: c1 }} />
            <div style={{ position: 'absolute', left: 0, top: 22, right: 0, bottom: 0, borderRadius: '8px 24px 24px 24px', background: `linear-gradient(135deg, ${c1}, ${c2})`, boxShadow: i === 0 && folderBump > 1 ? `0 0 50px ${c2}` : `0 16px 40px ${c2}33` }} />
            <Icon name="folder" size={34} color="rgba(10,10,16,.55)" style={{ position: 'absolute', right: 24, top: 52 }} />
            <div style={{ position: 'absolute', left: 24, bottom: 20, color: '#1a0e02' }}>
              <div style={{ fontSize: 28, fontWeight: 900 }}>{name}</div>
              <div style={{ fontSize: 20, fontWeight: 700, opacity: 0.7 }}>{i === 0 && f >= 112 ? Number(n) + 1 : n} projects</div>
            </div>
          </div>
        );
      })}
      {PROJECTS.map((name, i) => {
        const p = pop(f, 20 + i * 6, 12);
        const [c1, c2] = TINTS[[1, 0, 4][i]];
        const x = 140 + i * 340;
        const dragging = i === 1;
        const style: React.CSSProperties = dragging
          ? { transform: `translate(${cx - 635}px, ${cy - 435}px) scale(${scale})`, opacity: f < 106 ? Math.min(1, p * 2) : 1 - gone, zIndex: 30 }
          : { opacity: Math.min(1, p * 2), transform: `translateY(${(1 - p) * 60}px) scale(${0.85 + 0.15 * p})` };
        return (
          <React.Fragment key={name}>
            {dragging && f >= 80 ? <div style={{ position: 'absolute', left: x, top: 350, width: 310, height: 180, borderRadius: 24, border: '3px dashed rgba(255,255,255,.18)', opacity: ramp(f, 84, 100) }} /> : null}
            <div style={{ position: 'absolute', left: x, top: 350, width: 310, height: 180, borderRadius: 24, background: PANEL, border: `1px solid ${LINE}`, overflow: 'hidden', fontFamily: UI, boxShadow: dragging && grab > 0 ? '0 30px 60px rgba(0,0,0,.6)' : '0 12px 30px rgba(0,0,0,.35)', ...style }}>
              <div style={{ height: 112, background: `linear-gradient(135deg, ${c1}, ${c2})` }} />
              <div style={{ padding: '14px 20px', color: '#fff', fontSize: 24, fontWeight: 800 }}>{name}</div>
              <div style={{ position: 'absolute', right: 14, top: 14, width: 48, height: 48, borderRadius: 24, background: 'rgba(10,10,16,.45)', display: 'grid', placeItems: 'center' }}>
                <Icon name="star" size={28} color={dragging && star ? '#ffd23f' : '#fff'} fill={dragging && star} style={{ transform: dragging ? `scale(${star ? starPop : 1})` : undefined }} />
              </div>
              {dragging && star
                ? Array.from({ length: 8 }, (_, k) => {
                    const a = (k / 8) * Math.PI * 2;
                    const r = ramp(f, 52, 70, Easing.out(Easing.cubic));
                    return <div key={k} style={{ position: 'absolute', left: 310 - 38 + Math.cos(a) * r * 44, top: 38 + Math.sin(a) * r * 44, width: 9, height: 9, borderRadius: '50%', background: '#ffd23f', opacity: (1 - r) * (f >= 52 ? 1 : 0), transform: 'translate(-50%,-50%)' }} />;
                  })
                : null}
            </div>
          </React.Fragment>
        );
      })}
      {/* trash */}
      {(() => {
        const p = pop(f, 30, 12);
        return (
          <div style={{ position: 'absolute', left: 1200, top: 170, width: 580, height: 360, borderRadius: 26, border: '2px dashed rgba(255,255,255,.2)', background: 'rgba(255,255,255,.03)', fontFamily: UI, padding: 28, opacity: Math.min(1, p * 2), transform: `translateY(${(1 - p) * 60}px) scale(${0.9 + 0.1 * p})` }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 14, color: '#fff', fontSize: 30, fontWeight: 800 }}><Icon name="trash" size={34} color="#fb7185" /> Trash</div>
            {['Old draft.mp4', 'Test render.mp4'].map((name, i) => {
              const isFirst = i === 0;
              const out = isFirst ? ramp(f, 150, 170) : 0;
              const top = (isFirst ? 0 : 1) * 112 - (isFirst ? 0 : out0(f) * 112);
              return (
                <div key={name} style={{ position: 'absolute', left: 28, right: 28, top: 100 + top, height: 92, borderRadius: 18, background: restored && isFirst ? 'rgba(94,234,212,.16)' : 'rgba(255,255,255,.06)', display: 'flex', alignItems: 'center', padding: '0 20px', gap: 16, opacity: isFirst ? 1 - out : 1, transform: isFirst ? `translateX(${out * 120}px)` : undefined }}>
                  <div style={{ width: 48, height: 48, borderRadius: 12, background: `linear-gradient(135deg, ${TINTS[i + 3][0]}, ${TINTS[i + 3][1]})` }} />
                  <div style={{ color: '#d6d6e4', fontSize: 24, fontWeight: 700, flex: 1 }}>{name}</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 18px', borderRadius: 16, background: restored && isFirst ? '#5eead4' : GRAD, color: '#1a0e02', fontSize: 21, fontWeight: 800, transform: isFirst && f >= 146 && f < 158 ? 'scale(0.92)' : undefined }}>
                    <Icon name={restored && isFirst ? 'check' : 'restore'} size={22} color="#1a0e02" stroke={2.6} /> {restored && isFirst ? 'Restored' : 'Restore'}
                  </div>
                </div>
              );
            })}
          </div>
        );
      })()}
      {/* templates marquee */}
      <div style={{ position: 'absolute', left: 140, top: 566, color: MUTED, fontFamily: UI, fontSize: 24, fontWeight: 800, letterSpacing: '0.12em', opacity: tplIn }}>TEMPLATES</div>
      <div style={{ position: 'absolute', left: 0, top: 604, width: 1920, height: 160, overflow: 'hidden', opacity: tplIn }}>
        <div style={{ position: 'absolute', left: 0, top: 0, display: 'flex', gap: 24, transform: `translateX(${tx + (1 - tplIn) * 1500}px)` }}>
          {TEMPLATES.map((name, i) => {
            const [c1, c2] = TINTS[i % TINTS.length];
            return (
              <div key={name} style={{ flex: '0 0 270px', height: 156, borderRadius: 22, background: `linear-gradient(135deg, ${c1}, ${c2})`, position: 'relative', overflow: 'hidden', boxShadow: `0 14px 36px ${c2}44`, fontFamily: UI }}>
                <div style={{ position: 'absolute', left: 18, top: 16, width: 90, height: 12, borderRadius: 6, background: 'rgba(10,10,16,.35)' }} />
                <div style={{ position: 'absolute', left: 18, top: 38, width: 56, height: 8, borderRadius: 4, background: 'rgba(10,10,16,.22)' }} />
                <div style={{ position: 'absolute', right: -24, top: 20, width: 120, height: 120, borderRadius: '50%', background: 'rgba(255,255,255,.22)' }} />
                <div style={{ position: 'absolute', left: 18, bottom: 14, fontSize: 26, fontWeight: 900, color: '#1a0e02' }}>{name}</div>
              </div>
            );
          })}
        </div>
      </div>
      <Cursor
        pts={[
          { f: 30, x: 1000, y: 700 },
          { f: 48, x: 746, y: 350 + 38 },
          { f: 62, x: 746, y: 350 + 38 },
          { f: 72, x: 600, y: 470 },
          { f: 80, x: 635, y: 435 },
          { f: 112, x: 295, y: 240 },
          { f: 140, x: 1680, y: 296 },
          { f: 170, x: 1680, y: 296 },
          { f: 190, x: 1500, y: 700 }
        ]}
        clicks={[52, 76, 146]}
        hideAfter={175}
      />
      <KaraokeCaption text={t.captions[4]} start={24} />
    </>
  );
};
const out0 = (f: number): number => ramp(f, 158, 182);

/* ----------------------------------------------------------------- export */
export const ExportScene: React.FC = () => {
  const f = useCurrentFrame();
  const lang = useLang();
  const t = COPY[lang];
  const dlg = pop(f, 2, 14);
  const clicked = f >= 56;
  const prog = ramp(f, 62, 150, Easing.inOut(Easing.quad));
  const done = f >= 152;
  const pulse = !clicked ? 1 + 0.03 * Math.sin(f * 0.35) : 1;
  const fileIn = pop(f, 150, 9);
  const check = pop(f, 166, 7);
  const ready = pop(f, 176, 11);
  const press = f >= 56 && f < 64 ? 0.95 : 1;
  return (
    <>
      <StepTitle n={5} text={t.titles[4]} />
      <div style={{ opacity: Math.min(1, dlg * 1.5), transform: `translateY(${(1 - dlg) * 100}px) scale(${0.94 + 0.06 * dlg})` }}>
        <Win x={150} y={170} w={780} h={590} title="Export video">
          <div style={{ position: 'relative', fontFamily: UI }}>
            <div style={{ position: 'absolute', left: 44, top: 34, color: MUTED, fontSize: 22, fontWeight: 700 }}>Resolution</div>
            {['720p', '1080p', '4K'].map((s, i) => (
              <div key={s} style={{ position: 'absolute', left: 44 + i * 170, top: 76, width: 154, height: 56, borderRadius: 28, display: 'grid', placeItems: 'center', fontSize: 25, fontWeight: 800, background: i === 1 ? GRAD : 'rgba(255,255,255,.06)', color: i === 1 ? '#1a0e02' : '#cfcfe0', border: i === 1 ? 'none' : `1px solid ${LINE}`, transform: `scale(${pop(f, 14 + i * 4)})` }}>{s}</div>
            ))}
            <div style={{ position: 'absolute', left: 44, top: 164, color: MUTED, fontSize: 22, fontWeight: 700 }}>Format</div>
            <div style={{ position: 'absolute', left: 44, top: 204, display: 'flex', alignItems: 'center', gap: 12, color: '#fff', fontSize: 26, fontWeight: 700, opacity: ramp(f, 18, 34) }}>
              <Icon name="check" size={26} color="#5eead4" /> MP4  -  H.264  -  30 fps
            </div>
            <div style={{ position: 'absolute', left: 44, top: 310, width: 692, height: 96, borderRadius: 26, overflow: 'hidden', background: clicked ? 'rgba(255,255,255,.08)' : GRAD, boxShadow: clicked ? undefined : `0 14px 50px rgba(255,122,26,${0.4 + 0.3 * Math.sin(f * 0.35)})`, transform: `scale(${pulse * press})` }}>
              {clicked ? <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${prog * 100}%`, background: done ? 'linear-gradient(90deg,#34d399,#5eead4)' : GRAD }} /> : null}
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 14, color: '#1a0e02', fontSize: 38, fontWeight: 900, mixBlendMode: clicked && !done ? 'normal' : undefined }}>
                {!clicked ? (
                  <>
                    <Icon name="download" size={40} color="#1a0e02" stroke={2.6} /> Export MP4
                  </>
                ) : done ? (
                  <>
                    <Icon name="check" size={42} color="#052e22" stroke={3} /> Done
                  </>
                ) : (
                  <span style={{ color: '#fff', textShadow: '0 2px 6px rgba(0,0,0,.5)' }}>Rendering...  {Math.round(prog * 100)}%</span>
                )}
              </div>
            </div>
            <div style={{ position: 'absolute', left: 44, top: 436, color: MUTED, fontSize: 22, fontWeight: 600, opacity: ramp(f, 30, 50) }}>1920 x 1080  -  about 12 MB  -  no watermark</div>
          </div>
        </Win>
      </div>
      <Confetti f={f - 160} x={1390} y={330} />
      {f >= 150 ? (
        <div style={{ position: 'absolute', left: 1040, top: 250, width: 700, height: 340, borderRadius: 32, background: PANEL, border: `1px solid ${LINE}`, boxShadow: '0 40px 90px rgba(0,0,0,.55), 0 0 90px rgba(94,234,212,.15)', fontFamily: UI, opacity: Math.min(1, fileIn * 3), transform: `translateY(${(1 - fileIn) * -420}px) rotate(${(1 - fileIn) * -8}deg)` }}>
          <div style={{ position: 'absolute', left: 40, top: 44, width: 130, height: 160, borderRadius: 22, background: GRAD, boxShadow: '0 12px 40px rgba(255,122,26,.4)' }}>
            <div style={{ position: 'absolute', right: 0, top: 0, width: 40, height: 40, borderRadius: '0 22px 0 14px', background: 'rgba(255,255,255,.4)' }} />
            <div style={{ position: 'absolute', left: 0, right: 0, bottom: 28, textAlign: 'center', color: '#1a0e02', fontWeight: 900, fontSize: 40 }}>MP4</div>
            <Icon name="play" size={34} color="#1a0e02" fill style={{ position: 'absolute', left: 48, top: 38 }} />
          </div>
          <div style={{ position: 'absolute', left: 202, top: 56 }}>
            <div style={{ color: '#fff', fontSize: 36, fontWeight: 900 }}>coffee-app-demo.mp4</div>
            <div style={{ color: MUTED, fontSize: 25, fontWeight: 600, marginTop: 8 }}>1080p  -  0:30  -  12 MB</div>
          </div>
          <div style={{ position: 'absolute', left: 144, top: 148, width: 80, height: 80, borderRadius: '50%', background: '#34d399', display: 'grid', placeItems: 'center', border: `6px solid ${PANEL}`, transform: `scale(${check})`, boxShadow: '0 0 40px rgba(52,211,153,.6)' }}>
            <Icon name="check" size={44} color="#052e22" stroke={3.4} />
          </div>
          <div style={{ position: 'absolute', left: 40, bottom: 34, display: 'flex', alignItems: 'center', gap: 14, opacity: Math.min(1, ready * 2), transform: `translateY(${(1 - ready) * 30}px) scale(${0.8 + 0.2 * ready})`, transformOrigin: 'left center' }}>
            <div style={{ padding: '12px 26px', borderRadius: 30, background: 'rgba(52,211,153,.16)', border: '1px solid rgba(52,211,153,.6)', color: '#6ee7b7', fontSize: 28, fontWeight: 800, display: 'flex', alignItems: 'center', gap: 10 }}>
              <Icon name="sparkle" size={26} color="#6ee7b7" fill /> Ready to share
            </div>
            <div style={{ width: 54, height: 54, borderRadius: 18, background: 'rgba(255,255,255,.08)', display: 'grid', placeItems: 'center' }}><Icon name="link" size={26} /></div>
            <div style={{ width: 54, height: 54, borderRadius: 18, background: 'rgba(255,255,255,.08)', display: 'grid', placeItems: 'center' }}><Icon name="share" size={26} /></div>
          </div>
        </div>
      ) : null}
      <Cursor pts={[{ f: 20, x: 1300, y: 860 }, { f: 52, x: 150 + 44 + 346, y: 170 + 56 + 310 + 48 }]} clicks={[56]} hideAfter={96} />
      <KaraokeCaption text={t.captions[5]} start={24} />
    </>
  );
};

/* ------------------------------------------------------------------ outro */
export const OutroScene: React.FC = () => {
  const f = useCurrentFrame();
  const lang = useLang();
  const t = COPY[lang];
  const host = pop(f, 4, 12);
  const sun = pop(f, 12, 9);
  const word = pop(f, 22, 12);
  const cta = pop(f, 34, 9);
  const sweep = ((f - 40) % 60) / 60;
  const km = lang === 'km';
  return (
    <>
      <div style={{ position: 'absolute', left: 230, top: 120, width: 560, height: 650, borderRadius: 44, border: `1px solid ${LINE}`, background: `radial-gradient(90% 70% at 50% 100%, ${PHASE_THEME.payoff.glow}66, ${PANEL} 72%)`, boxShadow: '0 30px 90px rgba(0,0,0,.55), 0 0 100px rgba(255,122,26,.15)', opacity: Math.min(1, host * 2), transform: `translateY(${(1 - host) * 160}px) scale(${0.85 + 0.15 * host})` }}>
        <div style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, clipPath: 'inset(-120px -150px 0px -150px)' }}><div style={{ position: 'absolute', left: 50, top: 67, width: 460, height: 583 }}>
          <Presenter frame={Math.max(0, f - 4)} fps={30} mouthOpen={mouthAt(f, f > 20 && f < 100)} loudness={mouthAt(f, f > 20 && f < 100) * 0.7} talking={f > 20 && f < 100} phase="payoff" theme={PHASE_THEME.payoff} cueFrame={null} cueSide="up" celebrateFrom={14} />
        </div></div>
      </div>
      <div style={{ position: 'absolute', left: 900, top: 120, width: 800, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <div style={{ transform: `scale(${sun}) rotate(${(1 - sun) * -120}deg)`, marginTop: 10 }}>
          <SunMark size={190} rotate={f * 0.8} />
        </div>
        <div style={{ fontFamily: UI, fontWeight: 900, fontSize: 140, letterSpacing: '-0.03em', lineHeight: 1.3, marginTop: 24, opacity: Math.min(1, word * 2), transform: `translateY(${(1 - word) * 60}px)`, backgroundImage: 'linear-gradient(135deg,#fff 20%,#ffd9a8)', WebkitBackgroundClip: 'text', color: 'transparent' }}>Sorya</div>
        <div style={{ position: 'relative', marginTop: 40, padding: km ? '14px 56px 20px' : '22px 64px 26px', borderRadius: 70, background: GRAD, overflow: 'hidden', fontFamily: fontFor(lang), fontWeight: 900, fontSize: km ? 46 : 50, lineHeight: km ? 1.6 : 1.2, color: '#1a0e02', whiteSpace: 'nowrap', opacity: Math.min(1, cta * 2), transform: `scale(${(0.6 + 0.4 * cta) * (1 + 0.02 * Math.sin(f * 0.2))})`, boxShadow: `0 16px 70px rgba(255,122,26,${0.5 + 0.2 * Math.sin(f * 0.2)}), 0 0 0 8px rgba(255,179,64,.18)` }}>
          {t.cta}
          <div style={{ position: 'absolute', top: -20, bottom: -20, width: 120, left: `${sweep * 160 - 30}%`, background: 'linear-gradient(90deg, transparent, rgba(255,255,255,.75), transparent)', transform: 'skewX(-20deg)', opacity: f > 40 ? 1 : 0 }} />
        </div>
      </div>
      <KaraokeCaption text={t.captions[6]} start={26} />
    </>
  );
};
