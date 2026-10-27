import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { DemoBackground, LangContext, SceneFrame, type Enter } from './common';
import { DEMO_FRAMES, OVERLAP, SCENES, type Lang } from './copy';
import { DescribeScene, GenerateScene, IntroScene } from './scenesA';
import { EditScene, ExportScene, OrganiseScene, OutroScene } from './scenesB';

export { DEMO_FRAMES };
export type DemoProps = { lang: Lang };

const ORDER: { Scene: React.FC; enter: Enter }[] = [
  { Scene: IntroScene, enter: 'none' },
  { Scene: DescribeScene, enter: 'slide' },
  { Scene: GenerateScene, enter: 'sweep' },
  { Scene: EditScene, enter: 'iris' },
  { Scene: OrganiseScene, enter: 'slide' },
  { Scene: ExportScene, enter: 'sweep' },
  { Scene: OutroScene, enter: 'iris' }
];

export const SoryaDemo: React.FC<DemoProps> = ({ lang }) => (
  <LangContext.Provider value={lang}>
    <AbsoluteFill>
      <DemoBackground />
      {ORDER.map(({ Scene, enter }, i) => (
        <Sequence key={i} from={SCENES[i].start} durationInFrames={SCENES[i].length} layout="none">
          <AbsoluteFill>
            <SceneFrame length={SCENES[i].length} overlap={OVERLAP} enter={enter} exit={i < ORDER.length - 1}>
              <Scene />
            </SceneFrame>
          </AbsoluteFill>
        </Sequence>
      ))}
    </AbsoluteFill>
  </LangContext.Provider>
);
