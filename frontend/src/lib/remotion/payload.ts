/**
 * Turns editor scenes into the renderer's composition payload.
 *
 * Mirrors backend/app/services/render_payload.py, but with BROWSER media URLs
 * (image_url/audio_url) instead of the in-container ones the worker uses.
 * The result is validated by the renderer's own zod schema, so the preview
 * fails the same way an export would on a malformed scene.
 */
import { compositionSchema, type CompositionPayload } from '$renderer/schema';
import { layersOf, toRenderLayer } from '$lib/editor/layers';
import type { Project, Scene } from '$lib/types/api';

const num = (value: unknown, fallback: number): number =>
  typeof value === 'number' && Number.isFinite(value) ? value : fallback;

const MOODS = ['hook', 'setup', 'rising', 'twist', 'climax', 'payoff'];

type Speech = { narration?: string; words?: [string, number, number][]; mouth?: number[]; fps?: number };

/** Speech marks and loudness, only while they still describe the narration. */
const speechOf = (scene: Scene): Speech => {
  const speech = scene.settings?.speech as Speech | undefined;
  return speech && speech.narration === scene.narration ? speech : {};
};

export const buildPayload = (
  project: Pick<Project, 'title' | 'language' | 'fps' | 'width' | 'height'> &
    Partial<Pick<Project, 'purpose' | 'presenter' | 'cta_text' | 'music' | 'music_url'>>,
  scenes: Scene[]
): CompositionPayload => {
  const ordered = [...scenes].sort((a, b) => a.scene_number - b.scene_number);
  return compositionSchema.parse({
    project: {
      width: project.width,
      height: project.height,
      fps: project.fps,
      title: project.title,
      language: project.language,
      purpose: project.purpose ?? 'story',
      presenter: project.presenter ?? true,
      ctaText: project.cta_text ?? null,
      music: project.music?.enabled ?? true,
      musicUrl: project.music_url ?? null,
      musicVolume: project.music?.volume ?? 1,
      musicFadeIn: project.music?.fade_in ?? 0.4,
      musicFadeOut: project.music?.fade_out ?? 1,
      musicDuck: project.music?.duck ?? true
    },
    scenes: ordered.map((scene) => {
      const speech = speechOf(scene);
      return {
        id: scene.id,
        sceneNumber: scene.scene_number,
        duration: scene.duration,
        visualUrl: scene.video_url ?? scene.image_url,
        visualType: scene.video_url ? 'video' : scene.image_url ? 'image' : null,
        audioUrl: scene.audio_url,
        onScreenText: scene.on_screen_text,
        narration: scene.narration,
        captions: [...scene.captions]
          .sort((a, b) => a.start_time - b.start_time)
          .map((c) => ({ text: c.text, start: c.start_time, end: c.end_time })),
        transition: ['none', 'fade', 'slide'].includes(scene.transition) ? scene.transition : 'fade',
        backgroundColor: scene.background_color || '#0b0d12',
        words: (speech.words ?? []).map(([text, start, end]) => ({ text, start, end })),
        mouth: speech.mouth ?? [],
        mouthFps: speech.fps ?? 30,
        mood: MOODS.includes(scene.settings?.mood as string) ? scene.settings.mood : null,
        layers: layersOf(scene).map(toRenderLayer),
        audioStart: num(scene.settings?.audio_start, 0),
        voiceVolume: num(scene.settings?.voice_volume, 1),
        clipVolume: num(scene.settings?.clip_volume, 0),
        trimStart: num(scene.settings?.trim_start, 0),
        mediaFit: scene.settings?.media_fit === 'contain' ? 'contain' : 'cover',
        kenBurns: scene.settings?.ken_burns !== false
      };
    })
  });
};
