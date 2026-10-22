/**
 * One scene: backdrop, presenter, key-point sticker, captions and narration,
 * filmed by a virtual camera that pushes in slowly and punches in when the key
 * point lands.
 *
 * Layout respects short-video safe zones: in portrait the bottom fifth is
 * covered by the platform's caption and buttons, so nothing important lives there.
 */
import React from 'react';
import { AbsoluteFill, Audio, Easing, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { Backdrop } from '../components/Backdrop';
import { CaptionOverlay } from '../components/CaptionOverlay';
import { FollowCta } from '../components/FollowCta';
import { LayerView } from '../components/LayerView';
import { Presenter } from '../components/Presenter';
import { Sticker } from '../components/Sticker';
import type { Project, Scene } from '../schema';
import {
  PHASE_THEME,
  TRANSITION_FRAMES,
  ctaWindow,
  fontFor,
  loudnessAt,
  sceneMood,
  mouthOpenAt,
  speechSpan,
  stickerWindow
} from '../story';

const PURPOSE_BADGE: Record<Project['purpose'], string> = {
  story: 'STORY',
  product_demo: 'PRODUCT DEMO',
  social_post: 'SOCIAL',
  creator: 'CREATOR',
  explainer: 'EXPLAINER'
};

type Layout = {
  presenter: React.CSSProperties;
  sticker: React.CSSProperties;
  cta: React.CSSProperties;
  captionY: number;
  spot: { x: number; y: number };
  cueSide: 'up' | 'left' | 'right';
};

const layoutFor = (width: number, height: number, mirror: boolean): Layout => {
  if (height > width * 1.2) {
    return {
      presenter: { left: '10%', width: '80%', top: '29%', height: '58%' },
      sticker: { left: '6%', right: '6%', top: '11%', height: '17%' },
      cta: { left: '4%', right: '4%', top: '11%' },
      captionY: 0.725,
      spot: { x: 50, y: 50 },
      cueSide: 'up'
    };
  }
  if (width > height * 1.2) {
    const presenterLeft = mirror ? 56 : 8;
    return {
      presenter: { left: `${presenterLeft}%`, width: '36%', top: '12%', height: '90%' },
      sticker: mirror
        ? { left: '5%', right: '48%', top: '16%', height: '30%' }
        : { left: '48%', right: '5%', top: '16%', height: '30%' },
      cta: mirror ? { left: '4%', right: '48%', top: '20%' } : { left: '48%', right: '4%', top: '20%' },
      captionY: 0.8,
      spot: { x: presenterLeft + 18, y: 45 },
      cueSide: mirror ? 'left' : 'right'
    };
  }
  return {
    presenter: { left: '18%', width: '64%', top: '27%', height: '70%' },
    sticker: { left: '6%', right: '6%', top: '6%', height: '18%' },
    cta: { left: '4%', right: '4%', top: '7%' },
    captionY: 0.79,
    spot: { x: 50, y: 52 },
    cueSide: 'up'
  };
};

export const SceneView: React.FC<{
  scene: Scene;
  language: string;
  projectTitle: string;
  sceneCount: number;
  showCta: boolean;
  purpose?: Project['purpose'];
  /** Show the animated host. Off: the scene's picture fills the frame. */
  presenter?: boolean;
  /** Custom call-to-action button label; null keeps "Follow". */
  ctaText?: string | null;
}> = ({ scene, language, projectTitle, sceneCount, showCta, purpose = 'story', presenter = true, ctaText = null }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();
  const short = Math.min(width, height);
  const phase = sceneMood(scene, sceneCount);
  const theme = PHASE_THEME[phase];
  const framed = layoutFor(width, height, scene.sceneNumber % 2 === 0);
  // Without a host the picture is the subject: centre the camera on it.
  const layout: Layout = presenter
    ? framed
    : {
        ...framed,
        spot: { x: 50, y: 50 },
        // Landscape reserves one side for the host; centre the overlays instead.
        ...(width > height * 1.2
          ? {
              sticker: { left: '12%', right: '12%', top: '14%', height: '28%' },
              cta: { left: '12%', right: '12%', top: '20%' }
            }
          : {})
      };
  const isLast = scene.sceneNumber === sceneCount;

  // Voice-driven animation inputs.
  const span = speechSpan(scene);
  const t = frame / fps;
  const talking = span !== null && t >= span.start && t <= span.end + 0.1;
  const loudness = talking ? (scene.mouth.length > 0 ? loudnessAt(scene, frame, fps) : 0.5) : 0;
  const mouthOpen = mouthOpenAt(scene, frame, fps);

  const sticker = stickerWindow(scene, fps, durationInFrames);
  const cta = showCta && isLast ? ctaWindow(fps, durationInFrames) : null;
  // The CTA takes over the sticker's spot at the very end.
  const stickerShown = sticker && cta ? { ...sticker, end: Math.min(sticker.end, cta.start - 1) } : sticker;

  // --- camera -------------------------------------------------------------
  const push = interpolate(frame, [0, durationInFrames], [1, 1.04]);
  const age = sticker ? frame - sticker.start : -1;
  const punch = age < 0 ? 0 : interpolate(age, [0, 4, 16], [0, 0.07, 0.03], { extrapolateRight: 'clamp' });
  const shakeAmp = phase === 'hook' || phase === 'climax' ? 0.012 : 0.005;
  const shake = age >= 0 && age < 12 ? ((Math.sin(age * 2.7) * (12 - age)) / 12) * short * shakeAmp : 0;

  // --- entry transition ---------------------------------------------------
  const enter = interpolate(frame, [0, TRANSITION_FRAMES], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: Easing.out(Easing.cubic)
  });
  let entryTransform = 'none';
  let entryFilter: string | undefined;
  let entryOpacity = 1;
  // The first scene has no entry transition: it opens on a full frame, never
  // black, because platforms use the first frame as the default thumbnail and
  // it is what a scroller sees.
  const entering = scene.sceneNumber > 1;
  if (entering && scene.transition === 'slide') {
    // Whip pan: the new scene rushes in sideways with motion blur.
    entryTransform = `translateX(${(1 - enter) * 40}%)`;
    entryFilter = enter < 1 ? `blur(${(1 - enter) * 22}px)` : undefined;
  } else if (entering && scene.transition === 'fade') {
    // Zoom blur: the new scene settles from a bright, blurred close-up.
    entryTransform = `scale(${1 + (1 - enter) * 0.18})`;
    entryFilter = enter < 1 ? `blur(${(1 - enter) * 16}px) brightness(${1 + (1 - enter) * 0.6})` : undefined;
    entryOpacity = Math.min(1, enter * 1.5);
  }
  const outro = isLast
    ? interpolate(frame, [durationInFrames - 10, durationInFrames], [1, 0], {
        extrapolateLeft: 'clamp',
        extrapolateRight: 'clamp'
      })
    : 1;

  return (
    <AbsoluteFill style={{ backgroundColor: '#000', overflow: 'hidden' }}>
      <AbsoluteFill style={{ transform: entryTransform, filter: entryFilter, opacity: entryOpacity * outro }}>
        <AbsoluteFill
          style={{
            transform: `translate(${shake}px, ${shake * 0.6}px) scale(${push + punch})`,
            transformOrigin: `${layout.spot.x}% ${layout.spot.y}%`
          }}
        >
          <Backdrop
            scene={scene}
            theme={theme}
            phase={phase}
            frame={frame}
            durationInFrames={durationInFrames}
            loudness={loudness}
            spot={layout.spot}
            spotlight={presenter}
          />

          {presenter ? (
            <div style={{ position: 'absolute', ...layout.presenter, filter: 'drop-shadow(0 28px 40px rgba(0,0,0,.45))' }}>
              <Presenter
                frame={frame}
                fps={fps}
                mouthOpen={mouthOpen}
                loudness={loudness}
                talking={talking}
                phase={phase}
                theme={theme}
                cueFrame={sticker ? sticker.start : null}
                cueSide={layout.cueSide}
                celebrateFrom={cta ? cta.start : null}
              />
            </div>
          ) : null}
        </AbsoluteFill>

        {/* Overlays sit outside the camera so text never shakes or blurs. */}
        <div
          style={{
            position: 'absolute',
            top: '4.5%',
            left: '5%',
            maxWidth: '70%',
            padding: `${short * 0.008}px ${short * 0.02}px`,
            borderRadius: 999,
            background: 'rgba(0,0,0,.35)',
            border: '1px solid rgba(255,255,255,.18)',
            color: '#ffffffd9',
            fontFamily: fontFor(language),
            fontSize: short * 0.022,
            fontWeight: 700,
            letterSpacing: '0.06em',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis'
          }}
        >
          ✦ {PURPOSE_BADGE[purpose]} · {projectTitle.toUpperCase()}
        </div>

        {stickerShown && scene.onScreenText ? (
          <Sticker
            text={scene.onScreenText}
            theme={theme}
            language={language}
            frame={frame}
            fps={fps}
            window={stickerShown}
            box={layout.sticker}
            fontSize={short * (scene.sceneNumber === 1 ? 0.082 : 0.066)}
            loud={phase === 'hook' || phase === 'climax'}
          />
        ) : null}

        <CaptionOverlay
          captions={scene.captions}
          words={scene.words}
          language={language}
          accent={theme.accent}
          centerY={layout.captionY}
        />

        <LayerView layers={scene.layers} frame={frame} fps={fps} language={language} />

        {cta ? (
          <FollowCta
            frame={frame}
            fps={fps}
            start={cta.start}
            language={language}
            theme={theme}
            fontSize={short * 0.06}
            box={layout.cta}
            label={ctaText}
          />
        ) : null}
      </AbsoluteFill>

      {scene.audioUrl ? (
        // startFrom: after a split or trim the voice continues from where the cut
        // fell instead of restarting at the beginning of the file.
        <Audio
          src={scene.audioUrl}
          startFrom={Math.round(scene.audioStart * fps)}
          volume={scene.voiceVolume}
        />
      ) : null}
    </AbsoluteFill>
  );
};
