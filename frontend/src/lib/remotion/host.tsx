/**
 * The animated host, alive on the Home page.
 *
 * It is the very same host that appears in exported videos (any of the built-in avatars,
 * or the user's own photo), driven here by a looping, made-up "speech" instead of a real
 * voice track (see the renderer's HostLoop). Every 2.5 seconds it hops and changes mood.
 *
 * Imported lazily from HostAvatar.svelte (browser only), so React never runs on the server.
 */
import { Player } from '@remotion/player';
import { createRoot } from 'react-dom/client';
import { HostLoop, LOOP_FRAMES, BEAT_MS, HOST_LOOP_FPS } from '$renderer/components/HostLoop';
import type { AvatarPayload } from '$renderer/schema';

export { BEAT_MS };

export type HostController = { destroy: () => void };

export const mountHost = (
  element: HTMLElement,
  animate: boolean,
  avatar: AvatarPayload | null = null
): HostController => {
  const root = createRoot(element);
  root.render(
    <Player
      component={HostLoop}
      inputProps={{ avatar }}
      durationInFrames={LOOP_FRAMES}
      fps={HOST_LOOP_FPS}
      compositionWidth={600}
      compositionHeight={760}
      style={{ width: '100%', height: '100%', background: 'transparent' }}
      // Someone who asked their system for less motion gets a calm, still host.
      autoPlay={animate}
      loop
      controls={false}
      clickToPlay={false}
      initialFrame={animate ? 0 : 20}
      acknowledgeRemotionLicense
    />
  );
  return { destroy: () => root.unmount() };
};
