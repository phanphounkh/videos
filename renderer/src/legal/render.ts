/**
 * Renders one version of the legal demo from a plan JSON.
 *   tsx src/legal/render.ts <plan.json> <out.mp4> [publicDir]
 */
import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import fs from 'node:fs';
import path from 'node:path';

async function main(): Promise<void> {
  const [planPath, out, publicDir] = process.argv.slice(2);
  process.env.REMOTION_DISABLE_TELEMETRY = '1';
  const plan = JSON.parse(fs.readFileSync(planPath, 'utf8'));
  const serveUrl = await bundle({
    entryPoint: path.resolve(import.meta.dirname, 'index.ts'),
    publicDir: publicDir ? path.resolve(publicDir) : path.resolve(import.meta.dirname, '..', '..', 'public')
  });
  const chromiumOptions = { gl: (process.env.REMOTION_GL ?? 'swangle') as 'swangle' };
  const inputProps = { plan };
  const composition = await selectComposition({ serveUrl, id: 'LegalDemo', inputProps, chromiumOptions });
  let last = -1;
  await renderMedia({
    composition, serveUrl, inputProps, codec: 'h264', crf: 18, x264Preset: 'medium', audioCodec: 'aac', audioBitrate: '192k',
    concurrency: Number(process.env.REMOTION_CONCURRENCY ?? 3), chromiumOptions, timeoutInMilliseconds: 180_000,
    outputLocation: out,
    onProgress: ({ progress }) => { const pct = Math.floor(progress * 10) * 10; if (pct !== last) { last = pct; process.stdout.write(`${pct}%\n`); } }
  });
  process.stdout.write('done\n');
}
main().catch((e: unknown) => { console.error(e); process.exitCode = 1; });
