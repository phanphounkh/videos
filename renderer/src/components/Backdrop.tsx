/**
 * Everything behind the presenter: the scene image or video when there is one
 * (with a slow Ken Burns move), otherwise a living stage of drifting lights and
 * particles in the story beat's colours. A spotlight behind the presenter
 * breathes with the voice.
 */
import React from 'react';
import { AbsoluteFill, Img, OffthreadVideo, random, useVideoConfig } from 'remotion';
import type { Scene } from '../schema';
import type { PhaseTheme, StoryPhase } from '../story';

const PARTICLES = 26;

export const Backdrop: React.FC<{
  scene: Scene;
  theme: PhaseTheme;
  phase: StoryPhase;
  frame: number;
  durationInFrames: number;
  loudness: number;
  /** Presenter centre, in % of the frame, for the spotlight. */
  spot: { x: number; y: number };
  /** Rays and a voice-reactive glow behind the presenter. Off when nobody is on screen. */
  spotlight?: boolean;
}> = ({ scene, theme, phase, frame, durationInFrames, loudness, spot, spotlight = true }) => {
  const { fps } = useVideoConfig();
  const progress = frame / Math.max(1, durationInFrames);
  const energetic = phase === 'hook' || phase === 'climax';
  const isVideo = scene.visualType === 'video';
  const contain = scene.mediaFit === 'contain';
  // Slow zoom is for still pictures only: a screen recording must not drift.
  const zoom = !isVideo && scene.kenBurns;
  const fit = contain ? 'contain' : 'cover';

  return (
    <AbsoluteFill style={{ background: `linear-gradient(160deg,#07060c 0%,${theme.base} 55%,${scene.backgroundColor} 135%)` }}>
      {scene.visualUrl ? (
        <>
          {/* Letterboxed pictures get a blurred, dimmed copy of themselves behind them. */}
          {contain && !isVideo ? (
            <AbsoluteFill style={{ transform: 'scale(1.2)', filter: 'blur(28px) brightness(.55)' }}>
              <Img src={scene.visualUrl} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
            </AbsoluteFill>
          ) : null}
          <AbsoluteFill
            style={{
              transform: zoom
                ? `scale(${1.08 + progress * 0.1}) translate(${(scene.sceneNumber % 2 ? -1 : 1) * progress * 2}%, ${-progress * 1.5}%)`
                : undefined
            }}
          >
            {isVideo ? (
              <OffthreadVideo
                src={scene.visualUrl}
                // Skip what a split or trim cut away from the start of the clip.
                startFrom={Math.round(scene.trimStart * fps)}
                volume={scene.clipVolume}
                muted={scene.clipVolume === 0}
                style={{ width: '100%', height: '100%', objectFit: fit }}
              />
            ) : (
              <Img src={scene.visualUrl} style={{ width: '100%', height: '100%', objectFit: fit }} />
            )}
          </AbsoluteFill>
        </>
      ) : (
        <>
          {/* Slow coloured lights. */}
          {[0, 1, 2].map((i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                width: '75%',
                aspectRatio: '1',
                left: `${[-20, 45, 10][i] + Math.sin(frame / (70 + i * 23) + i) * 8}%`,
                top: `${[-10, 15, 55][i] + Math.cos(frame / (80 + i * 17) + i * 2) * 6}%`,
                borderRadius: '50%',
                background: `radial-gradient(circle, ${[theme.glow, theme.accent, theme.glow][i]}${['55', '2e', '3a'][i]} 0%, transparent 65%)`
              }}
            />
          ))}
          {/* Drifting dot grid gives depth and motion without distraction. */}
          <AbsoluteFill
            style={{
              opacity: 0.16,
              backgroundImage: 'radial-gradient(rgba(255,255,255,.9) 1.6px, transparent 1.8px)',
              backgroundSize: '44px 44px',
              backgroundPosition: `${frame * 0.4}px ${-frame * 0.8}px`,
              maskImage: 'linear-gradient(180deg, transparent, #000 25%, #000 70%, transparent)'
            }}
          />
        </>
      )}

      {/* Light rays behind the presenter on high-energy beats. */}
      {spotlight && energetic ? (
        <AbsoluteFill
          style={{
            opacity: 0.22,
            background: `repeating-conic-gradient(from ${frame * 0.6}deg at ${spot.x}% ${spot.y}%, ${theme.accent}55 0deg 6deg, transparent 6deg 18deg)`,
            maskImage: `radial-gradient(circle at ${spot.x}% ${spot.y}%, #000 10%, transparent 62%)`
          }}
        />
      ) : null}

      {/* Spotlight that swells as the presenter speaks. */}
      {spotlight ? (
        <AbsoluteFill
          style={{
            background: `radial-gradient(circle at ${spot.x}% ${spot.y}%, ${theme.glow}${Math.round(60 + loudness * 50).toString(16)} 0%, transparent ${34 + loudness * 6}%)`
          }}
        />
      ) : null}

      {/* Rising particles. */}
      {Array.from({ length: PARTICLES }, (_, i) => {
        const speed = 0.12 + random(`speed-${i}`) * 0.25;
        const size = 4 + random(`size-${i}`) * 10;
        const x = random(`x-${i}`) * 100 + Math.sin(frame / 30 + i) * 1.5;
        const y = 110 - ((random(`y-${i}`) * 120 + frame * speed) % 125);
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x}%`,
              top: `${y}%`,
              width: size,
              height: size,
              borderRadius: '50%',
              background: i % 3 === 0 ? theme.accent : '#ffffff',
              opacity: 0.12 + random(`o-${i}`) * 0.3,
              filter: `blur(${size > 10 ? 2 : 0}px)`
            }}
          />
        );
      })}

      {/* Vignette and a floor glow that grounds the presenter. */}
      <AbsoluteFill style={{ background: 'radial-gradient(ellipse at 50% 45%, transparent 50%, rgba(0,0,0,.6) 100%)' }} />
      <AbsoluteFill style={{ background: `linear-gradient(180deg, transparent 72%, ${theme.base}cc 92%, #000000ee 100%)` }} />
    </AbsoluteFill>
  );
};
