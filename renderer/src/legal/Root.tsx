import React from 'react';
import { Composition, type CalculateMetadataFunction } from 'remotion';
import { LegalDemo, type Plan } from './LegalDemo';

const empty: Plan = { fps: 30, total: 30, lang: 'en', clips: [], sfx: [], vo: [], caps: [] };
const meta: CalculateMetadataFunction<{ plan: Plan }> = ({ props }) => ({ durationInFrames: props.plan.total, fps: props.plan.fps, width: 1920, height: 1080 });

export const LegalRoot: React.FC = () => (
  <Composition id="LegalDemo" component={LegalDemo} durationInFrames={30} fps={30} width={1920} height={1080} defaultProps={{ plan: empty }} calculateMetadata={meta} />
);
