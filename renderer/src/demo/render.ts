/**
 * Renders the Sorya product demo in both languages.
 *
 *   npm run render:demo            (REMOTION_CONCURRENCY=2 by default)
 *
 * Writes sorya-demo-{en,km}.mp4 and a ~3s poster JPEG each into
 * ../frontend/static/demo/.
 */
import { bundle } from '@remotion/bundler';
import { renderMedia, renderStill, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

const OUT = path.resolve(import.meta.dirname, '..', '..', '..', 'frontend', 'static', 'demo');
const POSTER_FRAME = Number(process.env.DEMO_POSTER_FRAME ?? 95);

async function main(): Promise<void> {
  process.env.REMOTION_DISABLE_TELEMETRY = '1';
  fs.mkdirSync(OUT, { recursive: true });
  const serveUrl = await bundle({
    entryPoint: path.resolve(import.meta.dirname, '..', 'index.ts'),
    publicDir: path.resolve(import.meta.dirname, '..', '..', 'public')
  });
  const chromiumOptions = { gl: (process.env.REMOTION_GL ?? 'swangle') as 'swangle' };
  const concurrency = Number(process.env.REMOTION_CONCURRENCY ?? 2);
  const only = process.env.DEMO_LANGS?.split(',') ?? ['en', 'km'];

  for (const lang of ['en', 'km'] as const) {
    if (!only.includes(lang)) continue;
    const inputProps = { lang };
    const composition = await selectComposition({ serveUrl, id: 'SoryaDemo', inputProps, chromiumOptions });
    await renderStill({
      composition,
      serveUrl,
      inputProps,
      frame: POSTER_FRAME,
      imageFormat: 'jpeg',
      jpegQuality: 88,
      scale: 1280 / 1920,
      output: path.join(OUT, `sorya-demo-${lang}.jpg`),
      chromiumOptions
    });
    let last = -1;
    await renderMedia({
      composition,
      serveUrl,
      inputProps,
      codec: 'h264',
      crf: 23,
      x264Preset: 'medium',
      audioCodec: 'aac',
      audioBitrate: '128k',
      concurrency,
      chromiumOptions,
      timeoutInMilliseconds: 120_000,
      outputLocation: path.join(OUT, `sorya-demo-${lang}.mp4`),
      onProgress: ({ progress }) => {
        const pct = Math.floor(progress * 10) * 10;
        if (pct !== last) {
          last = pct;
          process.stdout.write(`[${lang}] ${pct}%\n`);
        }
      }
    });
    process.stdout.write(`[${lang}] done\n`);
  }
}

main().catch((e: unknown) => {
  console.error(e);
  process.exitCode = 1;
});
