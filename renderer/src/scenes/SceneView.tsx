/**
 * One scene: background visual + optional on-screen title + captions + voice.
 *
 * Everything is driven by the payload, so adding a new visual type later (video
 * clip, Ken Burns zoom, avatar) means extending this component, not the backend.
 */
import React from 'react';
import { AbsoluteFill, Audio, Img, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { CaptionOverlay } from '../components/CaptionOverlay';
import type { Scene } from '../schema';

export const SceneView: React.FC<{ scene: Scene; language: string }> = ({ scene, language }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  // A short fade in/out so cuts are not jarring. 0.4s on each side.
  const fadeFrames = Math.min(Math.round(0.4 * fps), Math.floor(durationInFrames / 3));
  const opacity =
    scene.transition === 'none'
      ? 1
      : interpolate(
          frame,
          [0, fadeFrames, durationInFrames - fadeFrames, durationInFrames],
          [0, 1, 1, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

  // Slow zoom (Ken Burns) keeps still images from looking like a slideshow.
  const scale = interpolate(frame, [0, durationInFrames], [1, 1.06], {
    extrapolateRight: 'clamp'
  });

  const isKhmer = language.startsWith('km');

  return (
    <AbsoluteFill style={{ backgroundColor: scene.backgroundColor, opacity }}>
      {scene.visualUrl ? (
        <AbsoluteFill style={{ overflow: 'hidden' }}>
          <Img
            src={scene.visualUrl}
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${scale})`
            }}
          />
          {/* Scrim: keeps white text readable over a bright image. */}
          <AbsoluteFill
            style={{
              background:
                'linear-gradient(180deg, rgba(0,0,0,0.35) 0%, rgba(0,0,0,0.1) 45%, rgba(0,0,0,0.55) 100%)'
            }}
          />
        </AbsoluteFill>
      ) : null}

      {scene.onScreenText ? (
        <AbsoluteFill
          style={{
            justifyContent: 'center',
            alignItems: 'center',
            padding: '0 10%',
            textShadow: '0 4px 24px rgba(0,0,0,0.7)'
          }}
        >
          <h1
            style={{
              color: '#ffffff',
              fontSize: 86,
              fontWeight: 700,
              textAlign: 'center',
              margin: 0,
              lineHeight: isKhmer ? 1.8 : 1.15,
              fontFamily: isKhmer
                ? "'Noto Sans Khmer', 'Khmer OS', sans-serif"
                : "'Inter', system-ui, sans-serif"
            }}
          >
            {scene.onScreenText}
          </h1>
        </AbsoluteFill>
      ) : null}

      <CaptionOverlay captions={scene.captions} language={language} />

      {scene.audioUrl ? <Audio src={scene.audioUrl} /> : null}
    </AbsoluteFill>
  );
};
