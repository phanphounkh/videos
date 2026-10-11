/** Presenter-led educational scene with timed emphasis text and captions. */
import React from 'react';
import { AbsoluteFill, Audio, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { CaptionOverlay } from '../components/CaptionOverlay';
import { EducationalAvatar } from '../components/EducationalAvatar';
import type { Scene } from '../schema';

type StoryPhase = 'hook' | 'setup' | 'rising' | 'twist' | 'climax' | 'payoff';

const PHASE_THEME: Record<StoryPhase, { label: string; base: string; glow: string; accent: string }> = {
  hook: { label: 'HOOK', base: '#2a0b12', glow: '#f97316', accent: '#fb923c' },
  setup: { label: 'SETUP', base: '#10172f', glow: '#3b82f6', accent: '#60a5fa' },
  rising: { label: 'RISING ACTION', base: '#062d2b', glow: '#14b8a6', accent: '#2dd4bf' },
  twist: { label: 'TWIST', base: '#2e1065', glow: '#a855f7', accent: '#c084fc' },
  climax: { label: 'CLIMAX', base: '#3f0a0a', glow: '#ef4444', accent: '#fb7185' },
  payoff: { label: 'PAYOFF', base: '#392008', glow: '#f59e0b', accent: '#fbbf24' }
};

export const getStoryPhase = (sceneNumber: number, sceneCount: number): StoryPhase => {
  if (sceneNumber <= 1) return 'hook';
  const progress = (sceneNumber - 1) / Math.max(1, sceneCount - 1);
  if (progress < 0.28) return 'setup';
  if (progress < 0.58) return 'rising';
  if (progress < 0.76) return 'twist';
  if (progress < 0.92) return 'climax';
  return 'payoff';
};

export const SceneView: React.FC<{ scene: Scene; language: string; projectTitle: string; sceneCount: number }> = ({
  scene,
  language,
  projectTitle,
  sceneCount
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const fadeFrames = Math.min(Math.round(0.4 * fps), Math.floor(durationInFrames / 3));
  const opacity = scene.transition === 'none'
    ? 1
    : interpolate(
        frame,
        [0, fadeFrames, durationInFrames - fadeFrames, durationInFrames],
        [0, 1, 1, 0],
        { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
      );

  const isKhmer = language.startsWith('km');
  const isPortrait = height > width;
  const scaleFactor = Math.min(width / 1920, height / 1080);
  const font = isKhmer
    ? "'Noto Sans Khmer', 'Khmer OS', sans-serif"
    : "'Inter', system-ui, sans-serif";
  const phase = getStoryPhase(scene.sceneNumber, sceneCount);
  const theme = PHASE_THEME[phase];
  const mirror = !isPortrait && scene.sceneNumber % 2 === 0;
  const backgroundDrift = interpolate(frame, [0, durationInFrames], [-2, 2], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp'
  });
  const hostScale = interpolate(frame, [0, durationInFrames], [0.98, 1.035], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp'
  });

  // onScreenText is the scene's important point. It enters shortly after the
  // narration begins, stays long enough to read, then gets out of the speaker's way.
  const popupStart = Math.min(Math.round(0.8 * fps), Math.round(durationInFrames * 0.18));
  const popupEnd = Math.min(
    durationInFrames - Math.max(1, fadeFrames),
    popupStart + Math.round(4.5 * fps)
  );
  const popupOpacity = scene.onScreenText
    ? interpolate(
        frame,
        [popupStart, popupStart + 8, Math.max(popupStart + 9, popupEnd - 8), popupEnd],
        [0, 1, 1, 0],
        { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
      )
    : 0;
  const popupScale = spring({
    frame: Math.max(0, frame - popupStart),
    fps,
    config: { damping: 13, stiffness: 180, mass: 0.7 },
    from: 0.72,
    to: 1
  });

  return (
    <AbsoluteFill
      style={{
        opacity,
        overflow: 'hidden',
        color: '#f8fafc',
        fontFamily: font,
        background: `radial-gradient(circle at ${24 + backgroundDrift}% 35%, ${theme.glow}55, transparent 32%), radial-gradient(circle at ${80 - backgroundDrift}% 20%, ${theme.accent}33, transparent 28%), linear-gradient(125deg, #08070d 0%, ${theme.base} 52%, ${scene.backgroundColor} 125%)`
      }}
    >
      <AbsoluteFill
        style={{
          opacity: 0.72,
          background: phase === 'climax'
            ? 'repeating-conic-gradient(from 210deg at 70% 48%, rgba(239,68,68,.16) 0deg 7deg, transparent 7deg 18deg)'
            : phase === 'twist'
              ? 'repeating-linear-gradient(135deg,rgba(168,85,247,.11) 0 3%,transparent 3% 10%)'
              : 'repeating-linear-gradient(90deg,rgba(255,255,255,.035) 0 5.5%,rgba(2,6,23,.22) 5.5% 10.5%,rgba(255,255,255,.025) 10.5% 16%)'
        }}
      />
      <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(90deg,rgba(245,158,11,.12),transparent 44%,rgba(37,99,235,.12))' }} />

      {/* Moving story lights make each narrative phase visually distinct. */}
      {[0, 1, 2].map((orb) => (
        <div
          key={orb}
          style={{
            position: 'absolute',
            right: `${8 + orb * 12}%`,
            top: `${18 + ((orb + scene.sceneNumber) % 3) * 17}%`,
            width: `${5 + orb * 2}%`,
            aspectRatio: '1',
            borderRadius: phase === 'twist' ? '18%' : '50%',
            border: `${Math.max(2, 3 * scaleFactor)}px solid ${theme.accent}66`,
            background: `${theme.glow}12`,
            boxShadow: `0 0 ${35 + orb * 15}px ${theme.glow}28`,
            transform: `translateY(${Math.sin((frame + orb * 24) / 25) * 12 * scaleFactor}px) rotate(${phase === 'twist' ? frame * 0.18 : 0}deg)`
          }}
        />
      ))}

      <div
        style={{
          position: 'absolute',
          top: '4.5%',
          left: '5%',
          right: '5%',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          letterSpacing: '0.08em',
          fontSize: 24 * scaleFactor,
          fontWeight: 700,
          color: '#cbd5e1'
        }}
      >
        <span>✦ KHMER STORY · {projectTitle.toUpperCase()}</span>
        <span style={{ color: theme.accent }}>SCENE {scene.sceneNumber} · {theme.label}</span>
      </div>

      <div
        style={{
          position: 'absolute',
          left: isPortrait ? '12%' : mirror ? '48%' : '8%',
          top: isPortrait ? '25%' : '15%',
          width: isPortrait ? '76%' : '46%',
          height: isPortrait ? '67%' : '80%',
          filter: 'drop-shadow(0 30px 45px rgba(2,6,23,.42))',
          transform: `scale(${hostScale})`,
          transformOrigin: 'center bottom'
        }}
      >
        <EducationalAvatar frame={frame} fps={fps} speaking={Boolean(scene.audioUrl)} mood={phase} />
      </div>

      {scene.onScreenText ? (
        <div
          style={{
            position: 'absolute',
            left: isPortrait ? '7%' : mirror ? '8%' : '50%',
            right: isPortrait ? '7%' : mirror ? '50%' : '8%',
            top: isPortrait ? '13%' : '31%',
            opacity: popupOpacity,
            transform: `scale(${popupScale}) translateY(${(1 - popupScale) * 24}px)`,
            transformOrigin: isPortrait ? 'center' : mirror ? 'right center' : 'left center',
            textAlign: isPortrait ? 'center' : 'left',
            padding: `${isPortrait ? 22 : 34}px ${isPortrait ? 28 : 44}px`,
            borderRadius: 999,
            background: `linear-gradient(115deg,${theme.glow}f2,${theme.base}f2)`,
            border: '2px solid rgba(255,255,255,.35)',
            boxShadow: `0 24px 70px ${theme.glow}55, inset 0 1px rgba(255,255,255,.4)`,
            color: '#fff7ed',
            fontSize: (isPortrait ? 42 : 58) * scaleFactor,
            lineHeight: isKhmer ? 1.7 : 1.15,
            fontWeight: 900,
            letterSpacing: isKhmer ? 0 : '-0.025em'
          }}
        >
          {scene.onScreenText}
        </div>
      ) : null}

      <div
        style={{
          position: 'absolute',
          left: 0,
          right: 0,
          bottom: 0,
          height: isPortrait ? '7%' : '10%',
          background: 'linear-gradient(180deg,#9a3412,#431407)',
          borderTop: `${4 * scaleFactor}px solid #fb923c`,
          boxShadow: '0 -18px 44px rgba(2,6,23,.55)'
        }}
      />

      <CaptionOverlay captions={scene.captions} language={language} />
      {scene.audioUrl ? <Audio src={scene.audioUrl} /> : null}
    </AbsoluteFill>
  );
};
