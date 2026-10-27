/** Who is signed in to the admin panel. Only administrators ever stay signed in here. */

import { goto } from '$app/navigation';
import { apiFetch, ApiError, getToken, setToken } from '$lib/api/client';

export interface AdminAccount {
  id: string;
  email: string;
  full_name: string | null;
  is_admin: boolean;
}

export const auth = $state<{ user: AdminAccount | null; ready: boolean; loading: boolean }>({
  user: null,
  ready: false,
  loading: false
});

export async function restoreSession(): Promise<void> {
  try {
    if (!getToken()) return;
    const me = await apiFetch<AdminAccount>('/auth/me');
    if (me.is_admin) auth.user = me;
    else setToken(null);
  } catch {
    setToken(null);
  } finally {
    auth.ready = true;
  }
}

export async function login(email: string, password: string): Promise<void> {
  auth.loading = true;
  try {
    const result = await apiFetch<{ access_token: string; user: AdminAccount }>('/auth/login', {
      method: 'POST',
      body: { email, password }
    });
    if (!result.user.is_admin) {
      throw new ApiError('NOT_ADMIN', 'This account is not an administrator.', 403);
    }
    setToken(result.access_token);
    auth.user = result.user;
  } finally {
    auth.loading = false;
  }
}

export function logout(): void {
  setToken(null);
  auth.user = null;
  void goto('/login');
}
