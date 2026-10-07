/**
 * Single HTTP entry point for the whole frontend.
 *
 * Components never call `fetch` directly: one client means one place for the
 * auth header, the error-envelope unwrapping and (later) retries or tracing.
 */

import type { ApiErrorBody } from '$lib/types/api';

const BASE = '/api';
const TOKEN_KEY = 'avs.token';

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/** Token lives in localStorage so a page reload keeps you signed in. */
export function getToken(): string | null {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof localStorage === 'undefined') return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

type Options = Omit<RequestInit, 'body'> & { body?: unknown; fetchFn?: typeof fetch };

export async function apiFetch<T>(path: string, options: Options = {}): Promise<T> {
  const { fetchFn = fetch, headers, body, ...rest } = options;

  const isForm = body instanceof FormData;
  const token = getToken();

  const response = await fetchFn(`${BASE}${path}`, {
    ...rest,
    body: isForm ? body : body === undefined ? undefined : JSON.stringify(body),
    headers: {
      Accept: 'application/json',
      ...(isForm ? {} : body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers
    }
  });

  if (response.status === 204) return undefined as T;

  const payload = await response.json().catch(() => null);

  if (!response.ok) {
    const envelope = payload as ApiErrorBody | null;
    throw new ApiError(
      envelope?.error?.code ?? 'UNKNOWN_ERROR',
      envelope?.error?.message ?? `Request failed with status ${response.status}`,
      response.status,
      envelope?.error?.details
    );
  }

  return payload as T;
}
