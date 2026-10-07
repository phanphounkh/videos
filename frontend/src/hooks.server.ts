/**
 * Server-side /api proxy.
 *
 * WHY this exists: the Vite dev server's `proxy` option only works in
 * development. In production (adapter-node, e.g. in Docker) the browser's
 * `fetch('/api/...')` hits THIS Node server, which would otherwise answer with
 * the SvelteKit app's HTML. Forwarding here keeps the browser on a single
 * origin, so there are no CORS preflights and no backend URL baked into the
 * client bundle.
 *
 * BACKEND_URL is an internal address (http://backend:8000 inside Docker) and is
 * never exposed to the browser.
 */

import type { Handle } from '@sveltejs/kit';

const BACKEND_URL = (process.env.BACKEND_URL ?? 'http://localhost:8000').replace(/\/$/, '');

// Hop-by-hop headers must not be forwarded.
const STRIP = new Set(['connection', 'keep-alive', 'transfer-encoding', 'upgrade', 'host']);

export const handle: Handle = async ({ event, resolve }) => {
  if (!event.url.pathname.startsWith('/api')) {
    return resolve(event);
  }

  const target = `${BACKEND_URL}${event.url.pathname}${event.url.search}`;
  const headers = new Headers();
  for (const [key, value] of event.request.headers) {
    if (!STRIP.has(key.toLowerCase())) headers.set(key, value);
  }

  try {
    const response = await fetch(target, {
      method: event.request.method,
      headers,
      // GET/HEAD must not carry a body; everything else is streamed through.
      body: ['GET', 'HEAD'].includes(event.request.method) ? undefined : event.request.body,
      // @ts-expect-error duplex is required by undici when streaming a body
      duplex: 'half',
      redirect: 'manual'
    });

    const out = new Headers(response.headers);
    out.delete('content-encoding');
    out.delete('content-length');
    return new Response(response.body, { status: response.status, headers: out });
  } catch (error) {
    return new Response(
      JSON.stringify({
        error: {
          code: 'BACKEND_UNREACHABLE',
          message: `Could not reach the API at ${BACKEND_URL}: ${String(error)}`
        }
      }),
      { status: 502, headers: { 'content-type': 'application/json' } }
    );
  }
};
