/**
 * The top-level composition: lays every scene on the timeline back to back.
 *
 * Remotion is React that renders frame by frame; <Sequence> is "show these
 * children from frame X for N frames", which is exactly a timeline clip.
 */
import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { SceneView } from './scenes/SceneView';
import type { CompositionPayload } from './schema';

export const secondsToFrames = (seconds: number, fps: number): number =>
  Math.max(1, Math.round(seconds * fps));

export const totalDurationInFrames = (payload: CompositionPayload): number =>
  payload.scenes.reduce(
    (sum, scene) => sum + secondsToFrames(scene.duration, payload.project.fps),
    0
  );

export const VideoComposition: React.FC<CompositionPayload> = ({ project, scenes }) => {
  let cursor = 0;

  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#000000'
      }}
    >
      {scenes.map((scene) => {
        const from = cursor;
        const frames = secondsToFrames(scene.duration, project.fps);
        cursor += frames;
        return (
          <Sequence key={scene.id} from={from} durationInFrames={frames}>
            <SceneView
              scene={scene}
              language={project.language}
              projectTitle={project.title}
              sceneCount={scenes.length}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};
