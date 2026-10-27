/**
 * Just the host, bust-cropped, no stage and no background: what the avatar pickers show
 * and what `npm run render:avatars` turns into transparent PNGs.
 */
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { z } from 'zod';
import { avatarSpec } from '../avatars';
import { PHASE_THEME, type StoryPhase } from '../story';
import { Host } from './Host';

export const avatarPreviewSchema = z.object({
  id: z.string().default('toon-m-young'),
  /** Test hooks: draw a photo avatar instead, or pose the host differently. */
  kind: z.enum(['builtin', 'photo']).default('builtin'),
  imageUrl: z.string().nullable().default(null),
  mode: z.enum(['mouth', 'subtle']).default('mouth'),
  frame: z.number().int().nonnegative().default(40),
  mouth: z.number().min(0).max(1).default(0.3),
  phase: z.enum(['hook', 'setup', 'rising', 'twist', 'climax', 'payoff']).default('setup'),
  /** false: the full-figure framing used on the stage. */
  bust: z.boolean().default(true)
});
export type AvatarPreviewProps = z.infer<typeof avatarPreviewSchema>;

export const AVATAR_PREVIEW_SIZE = { width: 480, height: 600 };

const BUST_VIEWBOX = { toon: '50 48 500 625', real: '70 -10 460 575' } as const;

export const AvatarPreview: React.FC<AvatarPreviewProps> = ({ id, kind, imageUrl, mode, frame, mouth, phase, bust }) => {
  const spec = avatarSpec(id);
  return (
    <AbsoluteFill>
      <Host
        avatar={{ kind, id, imageUrl, mode }}
        frame={frame}
        fps={30}
        mouthOpen={mouth}
        loudness={mouth * 0.8}
        talking={mouth > 0.05}
        phase={phase as StoryPhase}
        theme={PHASE_THEME.hook}
        cueFrame={null}
        cueSide="up"
        celebrateFrom={null}
        viewBox={bust && kind === 'builtin' ? BUST_VIEWBOX[spec.style] : undefined}
      />
    </AbsoluteFill>
  );
};
