/**
 * Mounts the renderer's Remotion composition inside the Svelte editor.
 *
 * WHY: a hand-written preview drifts from the real export. Running the very
 * same <VideoComposition> in @remotion/player means the preview IS the video,
 * including lip-sync, captions, music and sound effects.
 *
 * Imported lazily from VideoPreview.svelte (browser only), so React never
 * runs during server-side rendering.
 */
import { Player, type PlayerRef } from '@remotion/player';
import { createRoot } from 'react-dom/client';
import { VideoComposition, totalDurationInFrames } from '$renderer/VideoComposition';
import type { CompositionPayload } from '$renderer/schema';

export type PreviewHandlers = {
  onFrame: (frame: number) => void;
  onPlaying: (playing: boolean) => void;
};

export type PreviewController = {
  update: (payload: CompositionPayload) => void;
  seek: (frame: number) => void;
  toggle: () => void;
  destroy: () => void;
};

export const mountPreview = (
  element: HTMLElement,
  initial: CompositionPayload,
  handlers: PreviewHandlers
): PreviewController => {
  const root = createRoot(element);
  let current: PlayerRef | null = null;
  // A seek requested before the player has mounted is applied once it has.
  let pendingFrame: number | null = null;

  // Callback ref: React calls it when the player mounts (and with null when it
  // unmounts), which is the only reliable moment to wire events and seek.
  const attach = (player: PlayerRef | null) => {
    if (player === current) return;
    current = player;
    if (!player) return;
    player.addEventListener('frameupdate', (e) => handlers.onFrame(e.detail.frame));
    player.addEventListener('seeked', (e) => handlers.onFrame(e.detail.frame));
    player.addEventListener('play', () => handlers.onPlaying(true));
    player.addEventListener('pause', () => handlers.onPlaying(false));
    player.addEventListener('ended', () => handlers.onPlaying(false));
    if (pendingFrame !== null) player.seekTo(pendingFrame);
    pendingFrame = null;
  };

  const render = (payload: CompositionPayload) => {
    root.render(
      <Player
        ref={attach}
        component={VideoComposition}
        inputProps={payload}
        durationInFrames={Math.max(1, totalDurationInFrames(payload))}
        fps={payload.project.fps}
        compositionWidth={payload.project.width}
        compositionHeight={payload.project.height}
        style={{ width: '100%', height: '100%' }}
        clickToPlay
        spaceKeyToPlayOrPause={false}
      />
    );
  };

  render(initial);

  return {
    update: render,
    seek: (frame) => {
      if (current) current.seekTo(frame);
      else pendingFrame = frame;
    },
    toggle: () => current?.toggle(),
    destroy: () => root.unmount()
  };
};
