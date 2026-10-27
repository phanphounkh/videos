// Lists translation keys that exist in one language and not the other, and keys used in
// the source that exist in neither. Exit code 1 if anything is missing.
//   npm run check:i18n
import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const root = new URL('../src/lib/i18n/', import.meta.url).pathname;
const keysOf = (dir) => {
  const out = new Map();
  for (const f of readdirSync(join(root, dir)).filter((n) => n.endsWith('.ts'))) {
    const src = readFileSync(join(root, dir, f), 'utf8');
    for (const m of src.matchAll(/^\s*'([^']+)'\s*:/gm)) out.set(m[1], f);
  }
  return out;
};
const en = keysOf('en');
const km = keysOf('km');
let bad = 0;
for (const [k, f] of en) if (!km.has(k)) (console.log(`missing in km  ${k}  (${f})`), bad++);
for (const [k, f] of km) if (!en.has(k)) (console.log(`missing in en  ${k}  (${f})`), bad++);

// keys referenced from source: t('a.b'), tn('a.b', ...) -> a.b_one / a.b_other
const walk = (dir) =>
  readdirSync(dir, { withFileTypes: true }).flatMap((e) =>
    e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)]
  );
const src = new URL('../src/', import.meta.url).pathname;
for (const file of walk(src).filter((f) => /\.(svelte|ts)$/.test(f) && !f.includes('/i18n/'))) {
  const text = readFileSync(file, 'utf8');
  for (const m of text.matchAll(/\btn?\(\s*'([a-zA-Z0-9_.]+)'/g)) {
    const key = m[1];
    const isPlural = /\btn\(\s*'/.test(m[0]);
    const needed = isPlural ? [`${key}_one`, `${key}_other`] : [key];
    for (const k of needed) if (!en.has(k)) (console.log(`unknown key   ${k}  (${file.replace(src, '')})`), bad++);
  }
}
console.log(bad ? `\n${bad} problem(s)` : `i18n ok: ${en.size} keys in both languages`);
process.exit(bad ? 1 : 0);
