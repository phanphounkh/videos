/**
 * Registers the compositions Remotion knows about.
 */
import React from 'react';
import { Composition, Still, type CalculateMetadataFunction } from 'remotion';
import { VideoComposition, totalDurationInFrames } from './VideoComposition';
import { SoryaDemo, DEMO_FRAMES } from './demo/SoryaDemo';
import { ThumbnailView } from './components/ThumbnailView';
import { AVATAR_PREVIEW_SIZE, AvatarPreview, avatarPreviewSchema } from './components/AvatarPreview';
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
    <Still
      id="AvatarPreview"
      component={AvatarPreview}
      schema={avatarPreviewSchema}
      defaultProps={avatarPreviewSchema.parse({ id: 'toon-m-young' })}
      width={AVATAR_PREVIEW_SIZE.width}
      height={AVATAR_PREVIEW_SIZE.height}
    />
    <Composition id="SoryaDemo" component={SoryaDemo} durationInFrames={DEMO_FRAMES} fps={30} width={1920} height={1080} defaultProps={{ lang: 'en' as 'en' | 'km' }} />
    </>
  );
};
