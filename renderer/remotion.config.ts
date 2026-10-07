/**
 * Remotion build-time config (applies to `remotion studio` and the CLI).
 * The programmatic renderer in src/render.ts passes its own codec options.
 */
import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setChromiumOpenGlRenderer('angle');
