/**
 * Plays a template's cover live, for hover previews: the same drawing that made its
 * thumbnail picture, but running, so the host talks and blinks and the backdrop drifts.
 *
 * Imported lazily from AnimatedThumb.svelte (browser only), so React never runs on the server.
 */
import { Player } from '@remotion/player';
import { createRoot } from 'react-dom/client';
import { ThumbnailView } from '$renderer/components/ThumbnailView';
import type { ThumbnailPayload } from '$renderer/schema';
import type { TemplateItem } from '$lib/types/api';

const SHAPES: Record<string, [number, number]> = { '16:9': [1280, 720], '9:16': [720, 1280], '1:1': [1080, 1080] };

/** What the cover was drawn from (see backend scripts/render_template_thumbnails.py). */
const payloadFor = (t: TemplateItem): ThumbnailPayload => {
  const [width, height] = SHAPES[t.aspect_ratio] ?? SHAPES['16:9'];
  return {
    project: {
      width,
      height,
      fps: 30,
      title: t.title,
      language: 'en',
      music: false,
      cta: false,
      purpose: t.purpose,
      presenter: true,
      ctaText: null,
      musicUrl: null,
      musicVolume: 1,
      musicFadeIn: 0,
      musicFadeOut: 0,
      musicDuck: false,
      // The covers are drawn with the default host (the template script does the same).
      avatar: { kind: 'builtin', id: 'toon-m-young', imageUrl: null, mode: 'mouth' }
    },
    headline: t.headline,
    kicker: t.kicker,
    imageUrl: null,
    mood: t.mood,
    cta: null,
    animate: true
  };
};

export type ThumbController = { destroy: () => void };

export const mountThumb = (element: HTMLElement, template: TemplateItem): ThumbController => {
  const payload = payloadFor(template);
  const root = createRoot(element);
  root.render(
    <Player
      component={ThumbnailView}
      inputProps={payload}
      durationInFrames={120}
      fps={30}
      compositionWidth={payload.project.width}
      compositionHeight={payload.project.height}
      style={{ width: '100%', height: '100%' }}
      autoPlay
      loop
      controls={false}
      clickToPlay={false}
      acknowledgeRemotionLicense
    />
  );
  return { destroy: () => root.unmount() };
};
