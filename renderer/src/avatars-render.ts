/**
 * Renders a transparent 480x600 bust PNG of every built-in avatar, for the pickers in the web
 * app.
 *
 *   npm run render:avatars [outDir]
 *
 * Default outDir: ../frontend/static/avatars (files are <id>.png). Uses renderStill with
 * imageFormat 'png', which keeps the alpha channel.
 */
import { bundle } from '@remotion/bundler';
import { renderStill, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';
import { BUILTIN_AVATARS } from './avatars';

process.env.REMOTION_DISABLE_TELEMETRY ??= '1';

async function main(): Promise<void> {
  const outDir = path.resolve(process.argv[2] ?? path.resolve(import.meta.dirname, '..', '..', 'frontend', 'static', 'avatars'));
  fs.mkdirSync(outDir, { recursive: true });

  const serveUrl = await bundle({
    entryPoint: path.resolve(import.meta.dirname, 'index.ts'),
    publicDir: path.resolve(import.meta.dirname, '..', 'public')
  });
  const chromiumOptions = {
    gl: (process.env.REMOTION_GL ?? 'swangle') as 'swangle' | 'angle' | 'egl' | 'swiftshader' | 'vulkan' | 'angle-egl'
  };

  for (const avatar of BUILTIN_AVATARS) {
    const inputProps = { id: avatar.id };
    const composition = await selectComposition({ serveUrl, id: 'AvatarPreview', inputProps, chromiumOptions });
    const output = path.join(outDir, `${avatar.id}.png`);
    await renderStill({ composition, serveUrl, output, inputProps, imageFormat: 'png', frame: 0, chromiumOptions });
    process.stdout.write(`${JSON.stringify({ stage: 'avatar', id: avatar.id, output })}\n`);
  }
  process.stdout.write(`${JSON.stringify({ stage: 'completed', outDir })}\n`);
}

main().catch((error: unknown) => {
  process.stdout.write(`${JSON.stringify({ stage: 'failed', error: error instanceof Error ? error.message : String(error) })}\n`);
  process.exitCode = 1;
});
