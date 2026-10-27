/**
 * The cover image for a video.
 *
 * Built from the same parts as the video itself (backdrop, host, sticker, badge,
 * call-to-action chip) so a thumbnail always looks like the video it belongs to;
 * only the text changes. It is drawn at one settled frame, so it is a still, unless
 * `animate` is set (hover previews in the web app), which plays it.
 */
import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { Backdrop } from './Backdrop';
import { Host } from './Host';
import { Sticker } from './Sticker';
import type { Scene, ThumbnailPayload } from '../schema';
import { PHASE_THEME, fontFor } from '../story';

/** Far enough in for springs, particles and the host's idle sway to look natural. */
const STILL_FRAME = 40;

const sizeFor = (headline: string, short: number): number => {
  const length = [...headline].length;
  const scale = length <= 16 ? 0.125 : length <= 28 ? 0.1 : length <= 40 ? 0.085 : 0.072;
  return short * scale;
};

export const ThumbnailView: React.FC<ThumbnailPayload> = ({ project, headline, kicker, imageUrl, mood, cta, animate }) => {
  const { width, height, fps } = useVideoConfig();
  // A still is one settled frame. With `animate` the same picture comes alive: the host
  // talks (a made-up syllable rhythm), blinks and sways, and the backdrop drifts.
  const current = useCurrentFrame();
  const frame = animate ? STILL_FRAME + current : STILL_FRAME;
  const mouth = animate ? Math.abs(Math.sin(current * 0.62)) * (0.35 + 0.65 * Math.abs(Math.sin(current * 0.115))) : 0.55;
  const loud = animate ? mouth * 0.85 : 0.6;
  const short = Math.min(width, height);
  const theme = PHASE_THEME[mood];
  const wide = width > height * 1.2;
  const tall = height > width * 1.2;
  const host = project.presenter;

  // The backdrop only needs the picture and colour of a scene.
  const scene: Scene = {
    id: 'thumbnail',
    sceneNumber: 1,
    duration: 3,
    visualUrl: imageUrl,
    visualType: imageUrl ? 'image' : null,
    audioUrl: null,
    onScreenText: headline,
    narration: '',
    captions: [],
    transition: 'none',
    backgroundColor: '#0b0d12',
    words: [],
    mouth: [],
    mouthFps: 30,
    mood,
    layers: [],
    audioStart: 0,
    voiceVolume: 1,
    clipVolume: 0,
    trimStart: 0,
    mediaFit: 'cover',
    kenBurns: true
  };

  const layout = wide
    ? host
      ? {
          presenter: { left: '55%', width: '40%', top: '10%', height: '96%' },
          sticker: { left: '4%', right: '47%', top: '22%', height: '50%' } as React.CSSProperties,
          spot: { x: 75, y: 50 }
        }
      : {
          presenter: null,
          sticker: { left: '9%', right: '9%', top: '24%', height: '52%' } as React.CSSProperties,
          spot: { x: 50, y: 50 }
        }
    : host
      ? {
          presenter: { left: '8%', width: '84%', top: tall ? '36%' : '40%', height: tall ? '62%' : '58%' },
          sticker: { left: '5%', right: '5%', top: '8%', height: tall ? '26%' : '28%' } as React.CSSProperties,
          spot: { x: 50, y: 62 }
        }
      : {
          presenter: null,
          sticker: { left: '6%', right: '6%', top: '28%', height: '40%' } as React.CSSProperties,
          spot: { x: 50, y: 50 }
        };

  return (
    <AbsoluteFill style={{ backgroundColor: '#000', overflow: 'hidden' }}>
      <Backdrop
        scene={scene}
        theme={theme}
        phase={mood}
        frame={frame}
        durationInFrames={fps * 3}
        loudness={animate ? loud * 0.8 : 0.5}
        spot={layout.spot}
        spotlight={host}
      />

      {layout.presenter ? (
        <div style={{ position: 'absolute', ...layout.presenter, filter: 'drop-shadow(0 28px 40px rgba(0,0,0,.45))' }}>
          <Host
            avatar={project.avatar}
            frame={frame}
            fps={fps}
            mouthOpen={mouth}
            loudness={loud}
            talking
            phase={mood}
            theme={theme}
            cueFrame={null}
            cueSide={wide ? 'left' : 'up'}
            celebrateFrom={null}
          />
        </div>
      ) : null}

      {kicker ? (
        <div
          style={{
            position: 'absolute',
            top: '4.5%',
            left: '5%',
            maxWidth: '80%',
            padding: `${short * 0.01}px ${short * 0.026}px`,
            borderRadius: 999,
            background: 'rgba(0,0,0,.45)',
            border: '1px solid rgba(255,255,255,.28)',
            color: '#ffffffe6',
            fontFamily: fontFor(project.language),
            fontSize: short * 0.03,
            fontWeight: 800,
            letterSpacing: '0.08em',
            whiteSpace: 'nowrap',
            zIndex: 30
          }}
        >
          ✦ {kicker.toUpperCase()}
        </div>
      ) : null}

      <Sticker
        text={headline}
        theme={theme}
        language={project.language}
        frame={frame}
        fps={fps}
        window={{ start: 0, end: 100000 }}
        box={layout.sticker}
        fontSize={sizeFor(headline, short)}
        loud={false}
      />

      {cta ? (
        <div
          style={{
            position: 'absolute',
            left: '50%',
            bottom: tall ? '5%' : '6%',
            transform: 'translateX(-50%)',
            padding: `${short * 0.014}px ${short * 0.04}px`,
            borderRadius: 999,
            background: theme.accent,
            color: '#111018',
            fontFamily: fontFor(project.language),
            fontSize: short * 0.042,
            fontWeight: 900,
            whiteSpace: 'nowrap',
            boxShadow: '0 12px 36px rgba(0,0,0,.5)',
            border: `${Math.max(3, short * 0.005)}px solid #ffffff`,
            zIndex: 30
          }}
        >
          {cta} →
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
