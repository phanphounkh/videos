/**
 * The admin app's one HTTP entry point. Same-origin: `/api/*` is forwarded to the backend
 * and `/api/telemetry/*` to the telemetry service (see hooks.server.ts), so the browser
 * never learns either address and there is no CORS.
 */

const BASE = '/api';
const TOKEN_KEY = 'sorya.admin.token';

export interface ApiErrorBody {
  error?: { code: string; message: string; details?: Record<string, unknown> };
}

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

// A separate key from the user app's token: signing in here never signs anyone in there.
export function getToken(): string | null {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof localStorage === 'undefined') return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

type Options = Omit<RequestInit, 'body'> & { body?: unknown };

export async function apiFetch<T>(path: string, options: Options = {}): Promise<T> {
  const { headers, body, ...rest } = options;
  const token = getToken();
  const response = await fetch(`${BASE}${path}`, {
    ...rest,
    body: body === undefined ? undefined : JSON.stringify(body),
    headers: {
      Accept: 'application/json',
      ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers
    }
  });

  if (response.status === 204) return undefined as T;
  const payload = await response.json().catch(() => null);
  if (response.ok) return payload as T;

  // The backend answers { error: { code, message } }; the telemetry service { detail }.
  const envelope = payload as ApiErrorBody | null;
  const detail = typeof payload?.detail === 'string' ? payload.detail : undefined;
  throw new ApiError(
    envelope?.error?.code ?? 'UNKNOWN_ERROR',
    envelope?.error?.message ?? detail ?? `Request failed with status ${response.status}`,
    response.status,
    envelope?.error?.details
  );
}
