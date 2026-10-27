/**
 * A host made from the user's own photo.
 *
 * The picture sits in the same footprint as the cartoon hosts, as a rounded portrait with a
 * soft shadow. Cropped with object-fit: cover, so any image aspect works.
 *
 *  - mode 'mouth': the portrait breathes and sways, nods with the voice, and a stylised mouth
 *    is drawn over the lower face (at ~50% x, 74% y) and opens with `mouthOpen`, with a
 *    gentle blink-like vignette pulse.
 *  - mode 'subtle': breathing zoom plus a soft glowing ring and waveform that pulse with the
 *    voice. Nothing is drawn on the face.
 *
 * A pure function of the frame, like every other host.
 */
import React, { useState } from 'react';
import { Img } from 'remotion';
import { eyelid, type HostProps } from './hostMotion';

type Props = HostProps & {
  imageUrl: string | null;
  mode: 'mouth' | 'subtle';
};

const PlaceholderPerson: React.FC = () => (
  <svg viewBox="0 0 100 125" width="100%" height="100%" preserveAspectRatio="xMidYMid slice">
    <defs>
      <linearGradient id="ph-bg" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#3b4256" />
        <stop offset="1" stopColor="#1c2030" />
      </linearGradient>
    </defs>
    <rect width="100" height="125" fill="url(#ph-bg)" />
    <circle cx="50" cy="48" r="19" fill="#8a93aa" />
    <path d="M10 125 C12 86 32 76 50 76 C68 76 88 86 90 125 Z" fill="#8a93aa" />
  </svg>
);

export const PhotoPresenter: React.FC<Props> = ({
  frame,
  fps,
  mouthOpen,
  loudness,
  talking,
  theme,
  imageUrl,
  mode,
  celebrateFrom
}) => {
  const [failed, setFailed] = useState(false);
  const t = frame / fps;
  const loud = talking ? loudness : 0;
  const breathe = Math.sin(t * 2.1);
  const sway = Math.sin(t * 0.9);
  const celebrating = celebrateFrom !== null && frame >= celebrateFrom;
  const blink = 1 - eyelid(frame, fps); // 0..1 during a blink

  const subtle = mode === 'subtle';
  const zoom = 1.045 + breathe * (subtle ? 0.016 : 0.008) + loud * (subtle ? 0.02 : 0.012) + (celebrating ? 0.02 : 0);
  const nodY = talking && !subtle ? loud * 1.4 : 0; // % of height
  const swayX = subtle ? 0 : sway * 0.6;
  const swayRot = subtle ? 0 : sway * 0.35 + (talking ? Math.sin(t * 6.3) * loud * 0.4 : 0);

  const open = Math.min(1, mouthOpen);
  const mouthW = 76 - open * 12;
  const mouthH = 3.2 + open * 36;
  const glow = theme.glow;
  const accent = theme.accent;

  const bars = 11;
  const waveform = Array.from({ length: bars }, (_, i) => {
    const c = (i - (bars - 1) / 2) / ((bars - 1) / 2);
    const env = 1 - Math.abs(c) * 0.55;
    const v = 0.14 + (loud * 0.9 + 0.06) * (0.55 + 0.45 * Math.abs(Math.sin(frame * 0.35 + i * 1.7))) * env;
    return Math.min(1, v);
  });

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        containerType: 'size'
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: '1.5%',
          borderRadius: '9cqmin',
          overflow: 'hidden',
          background: '#161a26',
          boxShadow: subtle
            ? `0 0 ${3 + loud * 7}cqmin ${loud * 1.6}cqmin ${glow}${Math.round(60 + loud * 120).toString(16).padStart(2, '0')}, 0 3cqmin 7cqmin rgba(0,0,0,.45)`
            : '0 3cqmin 7cqmin rgba(0,0,0,.45), 0 0.6cqmin 1.6cqmin rgba(0,0,0,.35)',
          border: subtle ? `0.7cqmin solid ${accent}cc` : '0.5cqmin solid rgba(255,255,255,.55)'
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translate(${swayX}%, ${nodY}%) rotate(${swayRot}deg) scale(${zoom})`,
            transformOrigin: '50% 72%'
          }}
        >
          {imageUrl && !failed ? (
            <Img
              src={imageUrl}
              onError={() => setFailed(true)}
              style={{ width: '100%', height: '100%', objectFit: 'cover', objectPosition: '50% 30%', display: 'block' }}
            />
          ) : (
            <PlaceholderPerson />
          )}

          {!subtle ? (
            <svg
              viewBox="0 0 100 60"
              style={{
                position: 'absolute',
                left: '50%',
                top: '74%',
                width: '17cqmin',
                height: '10.2cqmin',
                transform: 'translate(-50%, -50%)',
                overflow: 'visible'
              }}
            >
              <defs>
                <filter id="lip-soft" x="-30%" y="-60%" width="160%" height="220%">
                  <feGaussianBlur stdDeviation="1.1" />
                </filter>
                <clipPath id="mouth-hole">
                  <ellipse cx="50" cy="30" rx={mouthW / 2} ry={Math.max(1.6, mouthH / 2)} />
                </clipPath>
              </defs>
              <g filter="url(#lip-soft)">
                {/* soft lip shape that opens with the voice */}
                <ellipse cx="50" cy="30" rx={mouthW / 2 + 3} ry={Math.max(3.2, mouthH / 2 + 3)} fill="#a84a52" opacity="0.55" />
                <ellipse cx="50" cy="30" rx={mouthW / 2} ry={Math.max(1.6, mouthH / 2)} fill="#2a0c12" opacity="0.92" />
              </g>
              <g clipPath="url(#mouth-hole)">
                <rect x="20" y="0" width="60" height={30 - mouthH / 2 + 6 + open * 3} fill="#f1ebe3" opacity={open > 0.18 ? 0.9 : 0} />
                <ellipse cx="50" cy={30 + mouthH * 0.3} rx={mouthW * 0.3} ry={3 + open * 7} fill="#b04a5a" opacity={open > 0.2 ? 0.9 : 0} />
              </g>
              <path
                d={`M${50 - mouthW / 2} 30 Q50 ${28 - open * 3} ${50 + mouthW / 2} 30`}
                fill="none"
                stroke="#2a0c12"
                strokeWidth="1.8"
                strokeLinecap="round"
                opacity="0.55"
              />
            </svg>
          ) : null}
        </div>

        {/* vignette, plus a blink-like pulse */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(ellipse at 50% 42%, rgba(0,0,0,0) 52%, rgba(0,0,0,.34) 100%)',
            pointerEvents: 'none'
          }}
        />
        {!subtle ? (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'radial-gradient(ellipse at 50% 42%, rgba(0,0,0,.0) 20%, rgba(0,0,0,.8) 100%)',
              opacity: blink * 0.4,
              pointerEvents: 'none'
            }}
          />
        ) : (
          <>
            <div
              style={{
                position: 'absolute',
                left: 0,
                right: 0,
                bottom: 0,
                height: '30%',
                background: 'linear-gradient(to top, rgba(0,0,0,.55), rgba(0,0,0,0))',
                pointerEvents: 'none'
              }}
            />
            <div
              style={{
                position: 'absolute',
                left: '50%',
                bottom: '5%',
                transform: 'translateX(-50%)',
                height: '8cqmin',
                display: 'flex',
                alignItems: 'center',
                gap: '1.1cqmin'
              }}
            >
              {waveform.map((v, i) => (
                <div
                  key={i}
                  style={{
                    width: '1.5cqmin',
                    height: `${Math.round(v * 100)}%`,
                    borderRadius: '1cqmin',
                    background: accent,
                    boxShadow: `0 0 1.6cqmin ${glow}`,
                    opacity: 0.55 + v * 0.45
                  }}
                />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
};
