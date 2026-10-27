/** The backend's admin API: people, plans, limits, and the headline user counts. */

import { apiFetch } from '$lib/api/client';

export type Metrics = { ai_calls: number; tokens: number; exports: number };

export interface AdminUser {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  plan: string;
  limit_ai_calls: number | null;
  limit_tokens: number | null;
  limit_exports: number | null;
  limit_storage_mb: number | null;
  created_at: string;
  last_login_at: string | null;
  project_count: number;
  used: Partial<Metrics>;
}

export interface UserDetail {
  user: AdminUser;
  recent_projects: { id: string; title: string; status: string; created_at: string }[];
}

export interface UserPatch {
  full_name?: string | null;
  is_active?: boolean;
  is_admin?: boolean;
  plan?: string;
  limit_ai_calls?: number | null;
  limit_tokens?: number | null;
  limit_exports?: number | null;
  limit_storage_mb?: number | null;
}

export interface Stats {
  users: number;
  active: number;
  admins: number;
  new_7d: number;
  projects: number;
}

export const users = {
  stats: () => apiFetch<Stats>('/admin/stats'),
  list: (p: { q?: string; status?: string; limit?: number; offset?: number }) => {
    const query = new URLSearchParams();
    if (p.q) query.set('q', p.q);
    if (p.status && p.status !== 'all') query.set('status', p.status);
    query.set('limit', String(p.limit ?? 50));
    query.set('offset', String(p.offset ?? 0));
    return apiFetch<{ items: AdminUser[]; total: number; limit: number; offset: number }>(
      `/admin/users?${query}`
    );
  },
  get: (id: string) => apiFetch<UserDetail>(`/admin/users/${id}`),
  update: (id: string, body: UserPatch) =>
    apiFetch<AdminUser>(`/admin/users/${id}`, { method: 'PATCH', body }),
  resetUsage: (id: string) =>
    apiFetch<void>(`/admin/users/${id}/reset-usage`, { method: 'POST' }),
  bulkRemove: (ids: string[]) =>
    apiFetch<{ deleted: number; skipped: { id: string; reason: string }[] }>(
      '/admin/users/bulk-delete',
      { method: 'POST', body: { ids } }
    ),
  remove: (id: string) => apiFetch<void>(`/admin/users/${id}`, { method: 'DELETE' })
};
