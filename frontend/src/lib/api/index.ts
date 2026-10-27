/** Typed wrappers around every endpoint the UI uses. */

import { apiFetch } from '$lib/api/client';
import type {
  AccountUsage,
  AvatarCatalog,
  AvatarMode,
  AvatarPreferences,
  CustomAvatar,
  ActivityItem,
  BulkAction,
  Folder,
  GenerateResponse,
  HealthResponse,
  MediaAsset,
  MusicSettings,
  Page,
  Project,
  ProjectDetail,
  ProjectView,
  PurposeTemplate,
  Storage,
  TemplateItem,
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

  // --- account ------------------------------------------------------------
  updateProfile: (body: { full_name: string | null }) =>
    apiFetch<User>('/account/profile', { method: 'PATCH', body }),
  /** Sets the profile picture (the server crops it to a square). */
  uploadAvatar: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiFetch<User>('/account/avatar', { method: 'POST', body: form });
  },
  removeAvatar: () => apiFetch<User>('/account/avatar', { method: 'DELETE' }),
  changePassword: (body: { current_password: string; new_password: string }) =>
    apiFetch<{ message: string }>('/account/password', { method: 'POST', body }),
  deleteAccount: (body: { password: string }) =>
    apiFetch<void>('/account', { method: 'DELETE', body }),
  myUsage: () => apiFetch<AccountUsage>('/account/usage'),

  // --- hosts (avatars) ------------------------------------------------------
  avatars: () => apiFetch<AvatarCatalog>('/avatars'),
  uploadHostAvatar: (file: File, opts: { name?: string; mode?: AvatarMode } = {}) => {
    const form = new FormData();
    form.append('file', file);
    if (opts.name) form.append('name', opts.name);
    if (opts.mode) form.append('mode', opts.mode);
    return apiFetch<CustomAvatar>('/avatars', { method: 'POST', body: form });
  },
  updateHostAvatar: (uuid: string, body: { name?: string; mode?: AvatarMode }) =>
    apiFetch<CustomAvatar>(`/avatars/${uuid}`, { method: 'PATCH', body }),
  deleteHostAvatar: (uuid: string) => apiFetch<void>(`/avatars/${uuid}`, { method: 'DELETE' }),
  saveAvatarPreferences: (body: AvatarPreferences) =>
    apiFetch<AvatarPreferences>('/account/avatar-preferences', { method: 'PUT', body }),

  // --- purposes -----------------------------------------------------------
  purposes: () => apiFetch<PurposeTemplate[]>('/purposes'),

  // --- projects -----------------------------------------------------------
  listProjects: (
    p: { view?: ProjectView; folder?: string; q?: string; sort?: 'recent' | 'title' | 'created' } = {}
  ) => {
    const query = new URLSearchParams({ limit: '100' });
    if (p.view && p.view !== 'all') query.set('view', p.view);
    if (p.folder) query.set('folder', p.folder);
    if (p.q) query.set('q', p.q);
    if (p.sort && p.sort !== 'recent') query.set('sort', p.sort);
    return apiFetch<Page<Project>>(`/projects?${query}`);
  },
  /** Many projects, one action: trash, restore, delete, star, unstar, move, duplicate. */
  bulkProjects: (ids: string[], action: BulkAction, folderId?: string | null) =>
    apiFetch<{ changed: number }>('/projects/bulk', {
      method: 'POST',
      body: { ids, action, folder_id: folderId ?? null }
    }),
  restoreProject: (id: string) =>
    apiFetch<Project>(`/projects/${id}/restore`, { method: 'POST' }),
  /** Skips the trash. */
  deleteProjectForever: (id: string) =>
    apiFetch<void>(`/projects/${id}?permanent=true`, { method: 'DELETE' }),
  emptyTrash: () => apiFetch<void>('/projects/trash', { method: 'DELETE' }),

  // --- folders ------------------------------------------------------------
  listFolders: () => apiFetch<Folder[]>('/folders'),
  createFolder: (name: string) => apiFetch<Folder>('/folders', { method: 'POST', body: { name } }),
  renameFolder: (id: string, name: string) =>
    apiFetch<Folder>(`/folders/${id}`, { method: 'PATCH', body: { name } }),
  deleteFolder: (id: string) => apiFetch<void>(`/folders/${id}`, { method: 'DELETE' }),

  // --- templates, storage, activity -----------------------------------------
  templates: () =>
    apiFetch<{ categories: string[]; templates: TemplateItem[] }>('/templates'),
  storage: () => apiFetch<Storage>('/account/storage'),
  activity: () => apiFetch<ActivityItem[]>('/account/activity'),
  createProject: (
    body: Partial<Project> & { title: string; resolution?: 'hd' | 'fhd'; folder_id?: string | null }
  ) =>
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
  ) =>
    apiFetch<GenerateResponse>(`/projects/${id}/generate`, {
      method: 'POST',
      body
    }),

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
    apiFetch<SceneMedia>(`/scenes/${sceneId}/generate-image`, {
      method: 'POST'
    }),
  generateSceneVoice: (sceneId: string) =>
    apiFetch<SceneMedia>(`/scenes/${sceneId}/generate-voice`, {
      method: 'POST'
    }),
  /** Replace a scene's captions with a hand-edited list (times are scene-relative seconds). */
  setCaptions: (
    sceneId: string,
    captions: { text: string; start_time: number; end_time: number }[]
  ) =>
    apiFetch<Scene>(`/scenes/${sceneId}/captions`, {
      method: 'PUT',
      body: { captions }
    }),
  /** Back to captions built from the narration. */
  resetCaptions: (sceneId: string) =>
    apiFetch<Scene>(`/scenes/${sceneId}/captions/reset`, { method: 'POST' }),
  splitScene: (sceneId: string, at: number) =>
    apiFetch<Scene[]>(`/scenes/${sceneId}/split`, {
      method: 'POST',
      body: { at }
    }),
  trimScene: (sceneId: string, start: number, end: number) =>
    apiFetch<Scene[]>(`/scenes/${sceneId}/trim`, {
      method: 'POST',
      body: { start, end }
    }),
  /** Makes the project match a snapshot exactly: undo and redo. */
  restoreTimeline: (projectId: string, snapshot: TimelineSnapshot) =>
    apiFetch<Scene[]>(`/projects/${projectId}/scenes/timeline`, {
      method: 'PUT',
      body: snapshot
    }),

  // --- media --------------------------------------------------------------
  listMedia: (projectId: string) => apiFetch<MediaAsset[]>(`/projects/${projectId}/assets`),
  /** Upload a file; with a scene id it replaces that scene's picture or clip. */
  uploadMedia: (projectId: string, file: File, sceneId?: string | null) => {
    const form = new FormData();
    form.append('project_id', projectId);
    if (sceneId) form.append('scene_id', sceneId);
    form.append('file', file);
    return apiFetch<MediaAsset>('/assets/upload', {
      method: 'POST',
      body: form
    });
  },
  uploadMusic: (projectId: string, file: File) => {
    const form = new FormData();
    form.append('file', file);
    return apiFetch<Project>(`/projects/${projectId}/music`, {
      method: 'POST',
      body: form
    });
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
