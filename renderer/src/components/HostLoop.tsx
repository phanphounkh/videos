/**
 * A looping, made-up "speech" for any avatar, for live previews in pickers and on the
 * Home page. Mount it in a Remotion <Player> (30 fps, LOOP_FRAMES long, 600x760).
 *
 * Every 2.5 seconds the host lands with a little hop and changes mood: the same beats the
 * Home page host has always used.
 */
import React from 'react';
import { AbsoluteFill, useVideoConfig } from 'remotion';
import { useCurrentFrame } from 'remotion';
import type { AvatarPayload } from '../schema';
import { PHASE_THEME, type StoryPhase } from '../story';
import { Host } from './Host';

export const HOST_LOOP_FPS = 30;
const SEGMENT = 75; // 2.5 s per beat
const BEATS: StoryPhase[] = ['hook', 'setup', 'rising', 'payoff', 'twist', 'payoff'];
export const LOOP_FRAMES = SEGMENT * BEATS.length;
/** Beat length in milliseconds, so a speech bubble in the page can follow along. */
export const BEAT_MS = (SEGMENT / HOST_LOOP_FPS) * 1000;

export const HostLoop: React.FC<{ avatar?: AvatarPayload | null }> = ({ avatar }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const beat = Math.floor(frame / SEGMENT) % BEATS.length;
  const local = frame % SEGMENT;
  const phase = BEATS[beat];

  // Talk for most of each beat, with a short pause at the end for a breath.
  const talking = local > 8 && local < SEGMENT - 14;
  // Syllables: fast open/close bursts whose strength rises and falls like words do.
  const word = Math.abs(Math.sin(local * 0.115 + beat));
  const mouthOpen = talking ? Math.abs(Math.sin(local * 0.62)) * (0.35 + 0.65 * word) : 0;
  const loudness = talking ? mouthOpen * 0.85 : 0;

  return (
    <AbsoluteFill>
      <Host
        avatar={avatar}
        frame={local}
        fps={fps}
        mouthOpen={mouthOpen}
        loudness={loudness}
        talking={talking}
        phase={phase}
        // The brand colours throughout; only the mood (face and gestures) changes per beat.
        theme={PHASE_THEME.hook}
        cueFrame={beat === 2 || beat === 4 ? 14 : null}
        cueSide="right"
        celebrateFrom={beat === BEATS.length - 1 ? 16 : null}
      />
    </AbsoluteFill>
  );
};
