import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  server: {
    host: '0.0.0.0',
    port: 5175,
    // Same-origin in development, like the frontend: the browser only ever calls /api/*.
    // Telemetry reads go to the telemetry service (same mapping as src/hooks.server.ts),
    // everything else to the backend.
    proxy: {
      '/api/telemetry': {
        target: process.env.TELEMETRY_URL ?? 'http://localhost:8006',
        changeOrigin: true,
        rewrite: (path) => {
          const rest = path.slice('/api/telemetry'.length);
          return /^\/health(\/|\?|$)/.test(rest) ? `/api/v1${rest}` : `/api/v1/telemetry${rest}`;
        }
      },
      '/api': {
        target: process.env.BACKEND_URL ?? 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
