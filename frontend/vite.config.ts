import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [tailwindcss(), sveltekit()],
  resolve: {
    // The renderer source ($renderer) imports these too. Resolve them all from
    // THIS package, never from ../renderer/node_modules: two copies of React
    // or Remotion in one page break hooks and the player.
    dedupe: ['react', 'react-dom', 'remotion', '@remotion/player', 'zod']
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    fs: { allow: ['..'] },
    // The browser calls /api/* on the SvelteKit origin and Vite forwards it to
    // FastAPI. That keeps us on one origin in development, so no CORS surprises.
    proxy: {
      // Browser events and the admin panel's reads go to the telemetry service. Listed
      // before '/api' so it wins. Same mapping as src/hooks.server.ts.
      '/api/telemetry': {
        target: process.env.TELEMETRY_URL ?? 'http://localhost:8006',
        changeOrigin: true,
        xfwd: true,
        rewrite: (path) => {
          const rest = path.slice('/api/telemetry'.length);
          return /^\/(ingest|health)(\/|\?|$)/.test(rest)
            ? `/api/v1${rest}`
            : `/api/v1/telemetry${rest}`;
        }
      },
      '/api': {
        target: process.env.BACKEND_URL ?? 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
