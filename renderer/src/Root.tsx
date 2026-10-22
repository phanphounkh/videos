/**
 * Registers the compositions Remotion knows about.
 */
import React from 'react';
import { Composition, Still, type CalculateMetadataFunction } from 'remotion';
import { VideoComposition, totalDurationInFrames } from './VideoComposition';
import { ThumbnailView } from './components/ThumbnailView';
import {
  compositionSchema,
  emptyComposition,
  emptyThumbnail,
  thumbnailSchema,
  type CompositionPayload,
  type ThumbnailPayload
} from './schema';

/**
 * Derives size/fps/duration from the payload at render time, so one composition
 * serves 16:9, 9:16 and 1:1 exports and any scene count.
 */
const calculateMetadata: CalculateMetadataFunction<CompositionPayload> = ({ props }) => ({
  durationInFrames: totalDurationInFrames(props),
  fps: props.project.fps,
  width: props.project.width,
  height: props.project.height
});

const thumbnailMetadata: CalculateMetadataFunction<ThumbnailPayload> = ({ props }) => ({
  width: props.project.width,
  height: props.project.height
});

export const RemotionRoot: React.FC = () => {
  return (
    <>
    <Still
      id="Thumbnail"
      component={ThumbnailView}
      schema={thumbnailSchema}
      defaultProps={emptyThumbnail}
      width={emptyThumbnail.project.width}
      height={emptyThumbnail.project.height}
      calculateMetadata={thumbnailMetadata}
    />
    <Composition
      id="VideoComposition"
      component={VideoComposition}
      schema={compositionSchema}
      defaultProps={emptyComposition}
      durationInFrames={totalDurationInFrames(emptyComposition)}
      fps={emptyComposition.project.fps}
      width={emptyComposition.project.width}
      height={emptyComposition.project.height}
      calculateMetadata={calculateMetadata}
    />
    </>
  );
};
