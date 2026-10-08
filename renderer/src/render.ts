/**
 * Headless render CLI — this is what the Python worker shells out to.
 *
 *   npx tsx src/render.ts <composition.json> <output.mp4>
 *
 * WHY a CLI and not an HTTP service: rendering is CPU-bound and long-running.
 * A process the worker owns gives us progress on stdout, a real exit code, and
 * no risk of an HTTP timeout cutting a render in half.
 *
 * Progress is printed as one JSON object per line so the Python worker can read
 * stdout line by line and update RenderJob.progress in the database.
 */
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import { compositionSchema } from './schema';

type Stage = 'preparing' | 'rendering' | 'completed' | 'failed';

const emit = (stage: Stage, progress: number, extra: Record<string, unknown> = {}): void => {
  process.stdout.write(`${JSON.stringify({ stage, progress, ...extra })}\n`);
};

async function main(): Promise<void> {
  const [payloadPath, outputPath] = process.argv.slice(2);

  if (!payloadPath || !outputPath) {
    throw new Error('usage: tsx src/render.ts <composition.json> <output.mp4>');
  }

  const raw = JSON.parse(fs.readFileSync(payloadPath, 'utf-8'));
  // Fail fast and loudly on a malformed payload instead of rendering garbage.
  const payload = compositionSchema.parse(raw);

  emit('preparing', 0, { scenes: payload.scenes.length });

  const serveUrl = await bundle({
    entryPoint: path.resolve(import.meta.dirname, 'index.ts'),
    onProgress: (p) => emit('preparing', Math.round(p * 0.1))
  });

  const chromiumOptions = {
    gl: (process.env.REMOTION_GL ?? 'swangle') as
      | 'swangle'
      | 'angle'
      | 'egl'
      | 'swiftshader'
      | 'vulkan'
      | 'angle-egl'
  };

  // Resource limits, tunable from the environment.
  //
  // concurrency: Remotion's default opens one Chromium tab per CPU core. Each
  // tab costs hundreds of MB, so on a memory-constrained host the machine
  // starts swapping and frames then exceed the per-frame timeout. One tab is
  // slower but survives; scale out with more worker containers instead.
  //
  // timeoutInMilliseconds: the per-frame budget. The default 30s is generous on
  // an idle machine and too tight on a loaded one, where fetching a scene's
  // image and audio can stall.
  const concurrency = Number(process.env.REMOTION_CONCURRENCY ?? 1);
  const frameTimeout = Number(process.env.REMOTION_FRAME_TIMEOUT_MS ?? 120_000);

  const composition = await selectComposition({
    serveUrl,
    id: 'VideoComposition',
    inputProps: payload,
    chromiumOptions,
    timeoutInMilliseconds: frameTimeout
  });

  fs.mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });

  await renderMedia({
    composition,
    serveUrl,
    codec: 'h264',
    outputLocation: outputPath,
    inputProps: payload,
    // FFmpeg-side settings: web-friendly MP4 with normalised AAC audio.
    audioCodec: 'aac',
    crf: 20,
    x264Preset: 'medium',
    concurrency,
    chromiumOptions,
    timeoutInMilliseconds: frameTimeout,
    onProgress: ({ progress }) => emit('rendering', 10 + Math.round(progress * 85))
  });

  emit('completed', 100, { output: path.resolve(outputPath) });
}

main().catch((error: unknown) => {
  emit('failed', 0, { error: error instanceof Error ? error.message : String(error) });
  process.exitCode = 1;
});
