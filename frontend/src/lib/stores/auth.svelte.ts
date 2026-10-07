/**
 * Authentication state.
 *
 * Svelte 5 runes in a `.svelte.ts` module: `$state` makes the object reactive
 * everywhere it is imported, which is simpler than a writable store for a
 * single global like the current user.
 */

import { goto } from '$app/navigation';
import { api } from '$lib/api';
import { getToken, setToken } from '$lib/api/client';
import type { User } from '$lib/types/api';

export const auth = $state<{ user: User | null; loading: boolean; ready: boolean }>({
  user: null,
  loading: false,
  ready: false
});

/** Called once on app start: turns a stored token back into a session. */
export async function restoreSession(): Promise<void> {
  if (!getToken()) {
    auth.ready = true;
    return;
  }
  try {
    auth.user = await api.me();
  } catch {
    setToken(null);
    auth.user = null;
  } finally {
    auth.ready = true;
  }
}

export async function login(email: string, password: string): Promise<void> {
  auth.loading = true;
  try {
    const result = await api.login({ email, password });
    setToken(result.access_token);
    auth.user = result.user;
  } finally {
    auth.loading = false;
  }
}

export async function register(
  email: string,
  password: string,
  fullName?: string
): Promise<void> {
  auth.loading = true;
  try {
    const result = await api.register({ email, password, full_name: fullName });
    setToken(result.access_token);
    auth.user = result.user;
  } finally {
    auth.loading = false;
  }
}

export async function logout(): Promise<void> {
  setToken(null);
  auth.user = null;
  await goto('/login');
}
