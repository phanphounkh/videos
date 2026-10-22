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
      '/api': {
        target: process.env.BACKEND_URL ?? 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
});
