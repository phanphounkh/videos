/**
 * Single HTTP entry point for the whole frontend.
 *
 * Components never call `fetch` directly: one client means one place for the
 * auth header, the error-envelope unwrapping and (later) retries or tracing.
 */

import { newRequestId, reportRequest, session } from '$lib/telemetry/client';
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

type Options = Omit<RequestInit, 'body'> & {
  body?: unknown;
  fetchFn?: typeof fetch;
};

export async function apiFetch<T>(path: string, options: Options = {}): Promise<T> {
  const { fetchFn = fetch, headers, body, ...rest } = options;

  const isForm = body instanceof FormData;
  const token = getToken();

  // Sent with every call so the server's events for it can be matched to this one
  // (and to the click that caused it): see lib/telemetry/client.ts.
  const requestId = newRequestId();
  const method = (rest.method ?? 'GET').toUpperCase();
  const started = performance.now();
  const report = (status: number, error?: string) =>
    reportRequest({
      method,
      path,
      status,
      duration_ms: performance.now() - started,
      request_id: requestId,
      error
    });

  let response: Response;
  try {
    response = await fetchFn(`${BASE}${path}`, {
      ...rest,
      body: isForm ? body : body === undefined ? undefined : JSON.stringify(body),
      headers: {
        Accept: 'application/json',
        ...(isForm ? {} : body !== undefined ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        'X-Request-ID': requestId,
        'X-Telemetry-Session': session(),
        ...headers
      }
    });
  } catch (error) {
    // The request never got an answer (offline, API down).
    report(0, error instanceof Error ? error.name : 'NETWORK_ERROR');
    throw error;
  }

  if (response.status === 204) {
    report(response.status);
    return undefined as T;
  }

  const payload = await response.json().catch(() => null);
  const envelope = response.ok ? null : (payload as ApiErrorBody | null);
  // The telemetry service answers in FastAPI's own shape: { detail: "..." }.
  const detail =
    !response.ok && typeof (payload as { detail?: unknown } | null)?.detail === 'string'
      ? (payload as { detail: string }).detail
      : undefined;
  report(response.status, envelope?.error?.code);

  if (!response.ok) {
    // A stored token the server no longer accepts (expired, or the JWT secret changed):
    // drop it and send the user to sign in again instead of showing a raw error.
    if (response.status === 401 && token && envelope?.error?.code === 'INVALID_TOKEN') {
      setToken(null);
      if (
        typeof window !== 'undefined' &&
        !['/login', '/register'].includes(window.location.pathname)
      ) {
        window.location.assign('/login');
      }
    }
    throw new ApiError(
      envelope?.error?.code ?? 'UNKNOWN_ERROR',
      envelope?.error?.message ?? detail ?? `Request failed with status ${response.status}`,
      response.status,
      envelope?.error?.details
    );
  }

  return payload as T;
}
