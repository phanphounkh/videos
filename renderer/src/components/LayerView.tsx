/**
 * The editor's text and sticker overlays for one scene.
 *
 * Each layer is on screen from `start` to `end` (scene-relative seconds), enters
 * with its chosen animation and fades out over its last few frames.
 */
import React from 'react';
import { Easing, interpolate, spring, useVideoConfig } from 'remotion';
import { layerPlacement, layerTextStyle } from '../layerStyle';
import type { Layer } from '../schema';

const EXIT_FRAMES = 6;

const OneLayer: React.FC<{ layer: Layer; frame: number; fps: number; language: string }> = ({
  layer,
  frame,
  fps,
  language
}) => {
  const { width, height } = useVideoConfig();
  const short = Math.min(width, height);
  const startFrame = Math.round(layer.start * fps);
  const endFrame = Math.round(layer.end * fps);
  if (frame < startFrame || frame >= endFrame) return null;

  const age = frame - startFrame;
  const remaining = endFrame - frame;
  let scale = 1;
  let opacity = 1;
  let lift = 0;

  switch (layer.animation) {
    case 'pop':
      scale = spring({ frame: age, fps, config: { damping: 9, stiffness: 210, mass: 0.7 } });
      break;
    case 'bounce': {
      const s = spring({ frame: age, fps, config: { damping: 6, stiffness: 160, mass: 0.8 } });
      scale = 0.6 + 0.4 * s;
      lift = (1 - s) * short * -0.05 + Math.sin((age / fps) * 4) * short * 0.006;
      opacity = interpolate(age, [0, 4], [0, 1], { extrapolateRight: 'clamp' });
      break;
    }
    case 'fade':
      opacity = interpolate(age, [0, 9], [0, 1], { extrapolateRight: 'clamp' });
      break;
    case 'slide_up': {
      const e = interpolate(age, [0, 12], [0, 1], {
        extrapolateRight: 'clamp',
        easing: Easing.out(Easing.cubic)
      });
      lift = (1 - e) * short * 0.06;
      opacity = e;
      break;
    }
    case 'none':
      break;
  }
  if (layer.animation !== 'none') {
    opacity *= interpolate(remaining, [0, EXIT_FRAMES], [0, 1], { extrapolateRight: 'clamp' });
  }

  return (
    <div
      style={{
        ...layerPlacement(layer),
        transform: `translate(-50%, -50%) translateY(${lift}px) rotate(${layer.rotation}deg) scale(${scale})`,
        opacity,
        zIndex: 25
      }}
    >
      <div style={layerTextStyle(layer, width, height, language)}>{layer.text}</div>
    </div>
  );
};

export const LayerView: React.FC<{ layers: Layer[]; frame: number; fps: number; language: string }> = ({
  layers,
  frame,
  fps,
  language
}) => (
  <>
    {layers.map((layer) => (
      <OneLayer key={layer.id} layer={layer} frame={frame} fps={fps} language={language} />
    ))}
  </>
);
