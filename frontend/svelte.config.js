import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
  preprocess: vitePreprocess(),
  kit: {
    // adapter-node builds a plain Node server, which is what we run in Docker.
    adapter: adapter(),
    alias: {
      $lib: 'src/lib'
    }
  }
};

export default config;
