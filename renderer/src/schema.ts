/**
 * The rendering contract between backend and renderer.
 *
 * WHAT: a zod schema for the "composition payload" — a self-contained JSON
 *       description of one video (size, fps, scenes, media URLs, captions).
 * WHY:  the renderer must never query the database. The backend worker builds
 *       this payload, hands it over, and the renderer is a pure function of it.
 *       Zod validates the payload so a malformed job fails immediately with a
 *       clear message instead of producing a broken MP4.
 */
import { z } from 'zod';

export const captionSchema = z.object({
  text: z.string(),
  start: z.number().nonnegative(),
  end: z.number().nonnegative()
});

export const sceneSchema = z.object({
  id: z.string(),
  /** Seconds. The renderer converts to frames using project.fps. */
  duration: z.number().positive(),
  /** Absolute URL (MinIO/S3 presigned) or null to fall back to a solid colour. */
  visualUrl: z.string().nullable().default(null),
  audioUrl: z.string().nullable().default(null),
  onScreenText: z.string().nullable().default(null),
  captions: z.array(captionSchema).default([]),
  transition: z.enum(['none', 'fade', 'slide']).default('fade'),
  backgroundColor: z.string().default('#0b0d12')
});

export const projectSchema = z.object({
  width: z.number().int().positive().default(1920),
  height: z.number().int().positive().default(1080),
  fps: z.number().int().positive().default(30),
  title: z.string().default('Untitled'),
  /** BCP-47-ish language tag. 'km' switches captions to the Khmer font stack. */
  language: z.string().default('en')
});

export const compositionSchema = z.object({
  project: projectSchema,
  scenes: z.array(sceneSchema).min(1)
});

export type Caption = z.infer<typeof captionSchema>;
export type Scene = z.infer<typeof sceneSchema>;
export type Project = z.infer<typeof projectSchema>;
export type CompositionPayload = z.infer<typeof compositionSchema>;

export const emptyComposition: CompositionPayload = {
  project: { width: 1920, height: 1080, fps: 30, title: 'Untitled', language: 'en' },
  scenes: [
    {
      id: 'placeholder',
      duration: 3,
      visualUrl: null,
      audioUrl: null,
      onScreenText: 'AI Video Studio',
      captions: [],
      transition: 'fade',
      backgroundColor: '#0b0d12'
    }
  ]
};
