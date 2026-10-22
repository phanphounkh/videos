/** Typed wrappers around every endpoint the UI uses. */

import { apiFetch } from '$lib/api/client';
import type {
  GenerateResponse,
  HealthResponse,
  MediaAsset,
  MusicSettings,
  Page,
  Project,
  ProjectDetail,
  PurposeTemplate,
  RenderJob,
  Scene,
  SceneMedia,
  TimelineSnapshot,
  TokenResponse,
  User
} from '$lib/types/api';

export const api = {
  health: () => apiFetch<HealthResponse>('/health'),

  // --- auth ---------------------------------------------------------------
  register: (body: { email: string; password: string; full_name?: string }) =>
    apiFetch<TokenResponse>('/auth/register', { method: 'POST', body }),
  login: (body: { email: string; password: string }) =>
    apiFetch<TokenResponse>('/auth/login', { method: 'POST', body }),
  me: () => apiFetch<User>('/auth/me'),

  // --- purposes -----------------------------------------------------------
  purposes: () => apiFetch<PurposeTemplate[]>('/purposes'),

  // --- projects -----------------------------------------------------------
  listProjects: () => apiFetch<Page<Project>>('/projects?limit=100'),
  createProject: (body: Partial<Project> & { title: string }) =>
    apiFetch<Project>('/projects', { method: 'POST', body }),
  getProject: (id: string) => apiFetch<Project>(`/projects/${id}`),
  getProjectDetail: (id: string) => apiFetch<ProjectDetail>(`/projects/${id}/detail`),
  updateProject: (id: string, body: Partial<Omit<Project, 'music'>> & { music?: MusicSettings }) =>
    apiFetch<Project>(`/projects/${id}`, { method: 'PATCH', body }),
  duplicateProject: (id: string) =>
    apiFetch<Project>(`/projects/${id}/duplicate`, { method: 'POST' }),
  deleteProject: (id: string) => apiFetch<void>(`/projects/${id}`, { method: 'DELETE' }),

  // --- generation ---------------------------------------------------------
  generate: (
    id: string,
    body: {
      prompt: string;
      duration: number;
      language: string;
      style: string;
      purpose?: string;
      presenter?: boolean;
      cta_text?: string | null;
      aspect_ratio?: string;
      tone?: string | null;
      audience?: string | null;
      generate_media: boolean;
    }
  ) => apiFetch<GenerateResponse>(`/projects/${id}/generate`, { method: 'POST', body }),

  // --- scenes -------------------------------------------------------------
  listScenes: (projectId: string) => apiFetch<Scene[]>(`/projects/${projectId}/scenes`),
  createScene: (projectId: string, body: Partial<Scene>) =>
    apiFetch<Scene>(`/projects/${projectId}/scenes`, { method: 'POST', body }),
  updateScene: (sceneId: string, body: Partial<Scene>) =>
    apiFetch<Scene>(`/scenes/${sceneId}`, { method: 'PATCH', body }),
  deleteScene: (sceneId: string) => apiFetch<void>(`/scenes/${sceneId}`, { method: 'DELETE' }),
  duplicateScene: (sceneId: string) =>
    apiFetch<Scene>(`/scenes/${sceneId}/duplicate`, { method: 'POST' }),
  reorderScenes: (projectId: string, sceneIds: string[]) =>
    apiFetch<Scene[]>(`/projects/${projectId}/scenes/reorder`, {
      method: 'POST',
      body: { scene_ids: sceneIds }
    }),
  generateSceneImage: (sceneId: string) =>
    apiFetch<SceneMedia>(`/scenes/${sceneId}/generate-image`, { method: 'POST' }),
  generateSceneVoice: (sceneId: string) =>
    apiFetch<SceneMedia>(`/scenes/${sceneId}/generate-voice`, { method: 'POST' }),
  /** Replace a scene's captions with a hand-edited list (times are scene-relative seconds). */
  setCaptions: (
    sceneId: string,
    captions: { text: string; start_time: number; end_time: number }[]
  ) => apiFetch<Scene>(`/scenes/${sceneId}/captions`, { method: 'PUT', body: { captions } }),
  /** Back to captions built from the narration. */
  resetCaptions: (sceneId: string) =>
    apiFetch<Scene>(`/scenes/${sceneId}/captions/reset`, { method: 'POST' }),
  splitScene: (sceneId: string, at: number) =>
    apiFetch<Scene[]>(`/scenes/${sceneId}/split`, { method: 'POST', body: { at } }),
  trimScene: (sceneId: string, start: number, end: number) =>
    apiFetch<Scene[]>(`/scenes/${sceneId}/trim`, { method: 'POST', body: { start, end } }),
  /** Makes the project match a snapshot exactly: undo and redo. */
  restoreTimeline: (projectId: string, snapshot: TimelineSnapshot) =>
    apiFetch<Scene[]>(`/projects/${projectId}/scenes/timeline`, { method: 'PUT', body: snapshot }),

  // --- media --------------------------------------------------------------
  listMedia: (projectId: string) => apiFetch<MediaAsset[]>(`/projects/${projectId}/assets`),
  /** Upload a file; with a scene id it replaces that scene's picture or clip. */
  uploadMedia: (projectId: string, file: File, sceneId?: string | null) => {
    const form = new FormData();
    form.append('project_id', projectId);
    if (sceneId) form.append('scene_id', sceneId);
    form.append('file', file);
    return apiFetch<MediaAsset>('/assets/upload', { method: 'POST', body: form });
  },
  uploadMusic: (projectId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiFetch<Project>(`/projects/${projectId}/music`, { method: 'POST', body: form });
  },
  removeMusic: (projectId: string) =>
    apiFetch<Project>(`/projects/${projectId}/music`, { method: 'DELETE' }),

  regenerateScene: (sceneId: string) =>
    apiFetch<SceneMedia[]>(`/scenes/${sceneId}/regenerate`, { method: 'POST' }),

  // --- renders ------------------------------------------------------------
  startRender: (projectId: string) =>
    apiFetch<{ job_id: string; status: string }>(`/projects/${projectId}/render`, {
      method: 'POST'
    }),
  getRenderJob: (jobId: string) => apiFetch<RenderJob>(`/render-jobs/${jobId}`),

  // --- assets -------------------------------------------------------------
  uploadAsset: (projectId: string, file: File, sceneId?: string) => {
    const form = new FormData();
    form.append('project_id', projectId);
    form.append('file', file);
    if (sceneId) form.append('scene_id', sceneId);
    return apiFetch<{ id: string; url: string | null }>('/assets/upload', {
      method: 'POST',
      body: form
    });
  }
};
