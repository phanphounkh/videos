/**
 * Types mirroring the backend's response models.
 *
 * The backend publishes OpenAPI at /openapi.json, so these can be generated
 * later; while the schema is still moving, a small hand-written file is easier
 * to read and review.
 */

export interface HealthResponse {
  status: string;
  app: string;
  environment: string;
  version: string;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: Record<string, unknown> };
}

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export type ProjectStatus =
  | 'draft'
  | 'generating'
  | 'ready'
  | 'rendering'
  | 'completed'
  | 'failed';

export type AspectRatio = '16:9' | '9:16' | '1:1';

export type VideoStyle =
  | 'educational'
  | 'cinematic'
  | 'documentary'
  | 'social_media'
  | 'minimal'
  | 'technology'
  | 'storytelling';

export type VideoPurpose = 'story' | 'product_demo' | 'social_post' | 'creator' | 'explainer';

/** A video purpose and the defaults the create form preselects (GET /api/purposes). */
export interface PurposeTemplate {
  key: VideoPurpose;
  label: string;
  description: string;
  aspect_ratio: AspectRatio;
  duration: number;
  style: VideoStyle;
  tone: string;
  audience: string;
  presenter: boolean;
  cta_text: string | null;
  example_prompt: string;
}

/** A text or sticker overlay. Times are seconds from the start of its scene. */
export interface Layer {
  id: string;
  type: 'text' | 'sticker';
  text: string;
  /** Centre, % of frame width / height. */
  x: number;
  y: number;
  /** % of the frame's short side. */
  font_size: number;
  rotation: number;
  color: string;
  background: string | null;
  weight: number;
  animation: 'none' | 'pop' | 'fade' | 'slide_up' | 'bounce';
  start: number;
  end: number;
}

export interface MusicSettings {
  enabled: boolean;
  volume: number;
  fade_in: number;
  fade_out: number;
  duck: boolean;
}

export const DEFAULT_MUSIC: MusicSettings = {
  enabled: true,
  volume: 1,
  fade_in: 0.4,
  fade_out: 1,
  duck: true
};

/** A file the user uploaded (GET /projects/{id}/assets). */
export interface MediaAsset {
  id: string;
  project_id: string;
  scene_id: string | null;
  type: 'image' | 'video' | 'audio' | 'music';
  source: string;
  mime_type: string;
  size_bytes: number;
  duration: number | null;
  width: number | null;
  height: number | null;
  original_filename: string | null;
  url: string | null;
  created_at: string;
}

export interface Project {
  id: string;
  title: string;
  description: string | null;
  prompt: string | null;
  status: ProjectStatus;
  language: string;
  aspect_ratio: string;
  style: string;
  purpose: VideoPurpose;
  presenter: boolean;
  cta_text: string | null;
  tone: string | null;
  audience: string | null;
  voice: string | null;
  target_duration: number;
  fps: number;
  width: number;
  height: number;
  duration: number;
  scene_count: number;
  thumbnail_url: string | null;
  music: MusicSettings;
  music_asset_id: string | null;
  music_url: string | null;
  music_name: string | null;
  music_duration: number | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Caption {
  id: string;
  segment_index: number;
  text: string;
  start_time: number;
  end_time: number;
  language: string;
}

export interface Scene {
  id: string;
  project_id: string;
  scene_number: number;
  narration: string;
  visual_prompt: string | null;
  on_screen_text: string | null;
  duration: number;
  start_time: number;
  transition: string;
  background_color: string;
  language: string | null;
  settings: Record<string, unknown>;
  image_url: string | null;
  audio_url: string | null;
  video_url: string | null;
  image_asset_id: string | null;
  video_asset_id: string | null;
  audio_asset_id: string | null;
  /** Length of the uploaded clip in seconds. */
  video_duration: number | null;
  captions: Caption[];
  created_at: string;
  updated_at: string;
}

export interface ProjectDetail {
  project: Project;
  scenes: Scene[];
}

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export type RenderStatus =
  | 'queued'
  | 'preparing'
  | 'rendering'
  | 'uploading'
  | 'completed'
  | 'failed';

export interface RenderJob {
  id: string;
  project_id: string;
  status: RenderStatus;
  progress: number;
  error_message: string | null;
  output_url: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface GenerateResponse {
  project_id: string;
  title: string;
  status: string;
  scene_count: number;
  duration: number;
  media_jobs_queued: number;
}

export interface SceneMedia {
  scene_id: string;
  asset_id: string | null;
  url: string | null;
  status: string;
  provider: string;
  message: string | null;
}

/** The whole timeline as one value: what undo and redo save and restore. */
export interface TimelineSnapshot {
  scenes: {
    id: string;
    narration: string;
    visual_prompt: string | null;
    on_screen_text: string | null;
    duration: number;
    transition: string;
    background_color: string;
    language: string | null;
    settings: Record<string, unknown>;
    image_asset_id: string | null;
    video_asset_id: string | null;
    audio_asset_id: string | null;
    captions: { text: string; start_time: number; end_time: number; language: string }[];
  }[];
  music_asset_id: string | null;
  music: MusicSettings;
}
