/**
 * The top-level composition: lays every scene on the timeline back to back,
 * then adds what spans scenes: the music bed, sound effects and progress bar.
 *
 * Remotion is React that renders frame by frame; <Sequence> is "show these
 * children from frame X for N frames", which is exactly a timeline clip.
 *
 * Sound design: the music sits low under the narration and rises in the gaps
 * (ducking); a whoosh covers each transition, a pop or impact lands with each
 * key-point sticker, and a ding marks the closing call to action. Effect
 * timings come from ./story, the same place the visuals read them.
 */
import React, { useMemo } from 'react';
import { AbsoluteFill, Audio, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { SceneView } from './scenes/SceneView';
import type { CompositionPayload } from './schema';
import { PHASE_THEME, TRANSITION_FRAMES, ctaWindow, sceneMood, speechSpan, stickerWindow } from './story';

export const secondsToFrames = (seconds: number, fps: number): number =>
  Math.max(1, Math.round(seconds * fps));

export const totalDurationInFrames = (payload: CompositionPayload): number =>
  payload.scenes.reduce(
    (sum, scene) => sum + secondsToFrames(scene.duration, payload.project.fps),
    0
  );

const MUSIC_FULL = 0.38;
const MUSIC_UNDER_VOICE = 0.13;
const SFX_VOLUME = { whoosh: 0.45, pop: 0.55, impact: 0.6, ding: 0.4 };

type Cue = { at: number; sound: keyof typeof SFX_VOLUME };

const ProgressBar: React.FC<{ total: number; color: string }> = ({ total, color }) => {
  const frame = useCurrentFrame();
  const { height, width } = useVideoConfig();
  const thickness = Math.max(6, Math.min(width, height) * 0.008);
  return (
    <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: thickness, background: 'rgba(255,255,255,.18)', zIndex: 50 }}>
      <div
        style={{
          width: `${(frame / Math.max(1, total - 1)) * 100}%`,
          height: '100%',
          background: `linear-gradient(90deg, ${color}, #ffffff)`,
          boxShadow: `0 0 ${thickness * 2}px ${color}`
        }}
      />
    </div>
  );
};

export const VideoComposition: React.FC<CompositionPayload> = ({ project, scenes }) => {
  const { fps } = project;
  const total = totalDurationInFrames({ project, scenes });

  const timeline = useMemo(() => {
    let cursor = 0;
    return scenes.map((scene) => {
      const from = cursor;
      const frames = secondsToFrames(scene.duration, fps);
      cursor += frames;
      return { scene, from, frames };
    });
  }, [scenes, fps]);

  const cues = useMemo(() => {
    const out: Cue[] = [];
    timeline.forEach(({ scene, from, frames }, index) => {
      // Centre the whoosh on the cut so it starts while the old scene is up.
      if (index > 0 && scene.transition !== 'none') out.push({ at: from - Math.round(TRANSITION_FRAMES / 2), sound: 'whoosh' });
      const sticker = stickerWindow(scene, fps, frames);
      if (sticker) {
        const phase = sceneMood(scene, scenes.length);
        out.push({ at: from + sticker.start, sound: phase === 'hook' || phase === 'climax' ? 'impact' : 'pop' });
      }
      if (project.cta && index === timeline.length - 1) out.push({ at: from + ctaWindow(fps, frames).start, sound: 'ding' });
    });
    return out.filter((cue) => cue.at >= 0);
  }, [timeline, fps, scenes.length, project.cta]);

  // Per-frame "is someone talking" mask for ducking, softened so the music
  // glides rather than jumps.
  const duck = useMemo(() => {
    const raw = new Float32Array(total);
    for (const { scene, from } of timeline) {
      const span = speechSpan(scene);
      if (!span) continue;
      const start = from + Math.round(span.start * fps) - 4;
      const end = from + Math.round(span.end * fps) + 6;
      for (let f = Math.max(0, start); f < Math.min(total, end); f++) raw[f] = 1;
    }
    const soft = new Float32Array(total);
    const radius = 8;
    for (let f = 0; f < total; f++) {
      let sum = 0;
      let n = 0;
      for (let k = -radius; k <= radius; k++) {
        const i = f + k;
        if (i >= 0 && i < total) {
          sum += raw[i];
          n++;
        }
      }
      soft[f] = sum / n;
    }
    return soft;
  }, [timeline, total, fps]);

  const musicVolume = (frame: number): number => {
    const underVoice = project.musicDuck ? (duck[Math.min(frame, total - 1)] ?? 0) : 0;
    const ducked = MUSIC_FULL + (MUSIC_UNDER_VOICE - MUSIC_FULL) * underVoice;
    // Fades are in seconds. Clamp so a long fade on a short video cannot cross.
    const fadeIn = Math.min(Math.round(project.musicFadeIn * fps), Math.floor(total / 2));
    const fadeOut = Math.min(Math.round(project.musicFadeOut * fps), Math.floor(total / 2));
    const fade = interpolate(frame, [0, Math.max(1, fadeIn), total - Math.max(1, fadeOut), total], [fadeIn ? 0 : 1, 1, 1, fadeOut ? 0 : 1], {
      extrapolateLeft: 'clamp',
      extrapolateRight: 'clamp'
    });
    return ducked * fade * project.musicVolume;
  };

  const lastPhase = sceneMood(scenes[scenes.length - 1], scenes.length);

  return (
    <AbsoluteFill style={{ backgroundColor: '#000000' }}>
      {timeline.map(({ scene, from, frames }) => (
        <Sequence key={scene.id} from={from} durationInFrames={frames}>
          <SceneView
            scene={scene}
            language={project.language}
            projectTitle={project.title}
            sceneCount={scenes.length}
            showCta={project.cta}
            purpose={project.purpose}
            presenter={project.presenter}
            ctaText={project.ctaText}
          />
        </Sequence>
      ))}

      {project.music && project.musicVolume > 0 ? (
        <Audio src={project.musicUrl ?? staticFile('studio/music/bed.wav')} loop volume={musicVolume} />
      ) : null}

      {cues.map((cue, index) => (
        <Sequence key={`${cue.sound}-${index}`} from={cue.at} durationInFrames={Math.round(1.5 * fps)}>
          <Audio src={staticFile(`studio/sfx/${cue.sound}.wav`)} volume={SFX_VOLUME[cue.sound]} />
        </Sequence>
      ))}

      <ProgressBar total={total} color={PHASE_THEME[lastPhase].accent} />
    </AbsoluteFill>
  );
};
