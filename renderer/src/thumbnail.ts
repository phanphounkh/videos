/**
 * Thumbnail CLI — what the Python worker shells out to for a project cover.
 *
 *   npx tsx src/thumbnail.ts <thumbnail.json> <output.jpg>
 *
 * Prints one JSON object per line like render.ts: {stage:'completed', output}
 * on success, {stage:'failed', error} and a non-zero exit code on failure.
 */
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import { thumbnailSchema } from './schema';

const emit = (stage: string, extra: Record<string, unknown> = {}): void => {
  process.stdout.write(`${JSON.stringify({ stage, ...extra })}\n`);
};

async function main(): Promise<void> {
  const [payloadPath, outputPath] = process.argv.slice(2);
  if (!payloadPath || !outputPath) {
    throw new Error('usage: tsx src/thumbnail.ts <thumbnail.json> <output.jpg>');
  }

  const payload = thumbnailSchema.parse(JSON.parse(fs.readFileSync(payloadPath, 'utf-8')));
  emit('preparing');

  const serveUrl = await bundle({
    entryPoint: path.resolve(import.meta.dirname, 'index.ts'),
    publicDir: path.resolve(import.meta.dirname, '..', 'public')
  });
  const chromiumOptions = {
    gl: (process.env.REMOTION_GL ?? 'swangle') as 'swangle' | 'angle' | 'egl' | 'swiftshader' | 'vulkan' | 'angle-egl'
  };
  const timeoutInMilliseconds = Number(process.env.REMOTION_FRAME_TIMEOUT_MS ?? 120_000);

  const composition = await selectComposition({
    serveUrl,
    id: 'Thumbnail',
    inputProps: payload,
    chromiumOptions,
    timeoutInMilliseconds
  });

  fs.mkdirSync(path.dirname(path.resolve(outputPath)), { recursive: true });
  await renderStill({
    composition,
    serveUrl,
    output: outputPath,
    inputProps: payload,
    imageFormat: 'jpeg',
    jpegQuality: 92,
    frame: 0,
    chromiumOptions,
    timeoutInMilliseconds
  });

  emit('completed', { output: path.resolve(outputPath) });
}

main().catch((error: unknown) => {
  emit('failed', { error: error instanceof Error ? error.message : String(error) });
  process.exitCode = 1;
});
