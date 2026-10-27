/**
 * Hosts ("avatars"): one shared copy of the catalogue (built-in hosts, the user's own
 * uploads and their preferences), plus the rules that turn "automatic" into a real host
 * on the client, mirroring the server so the Create form can preview the result.
 */
import { api } from '$lib/api';
import type {
  AvatarAge,
  AvatarCatalog,
  AvatarGender,
  AvatarPreferences,
  AvatarStyle,
  BuiltinAvatar,
  CustomAvatar
} from '$lib/types/api';

const person = (
  style: AvatarStyle,
  gender: AvatarGender,
  age: AvatarAge,
  name: string
): BuiltinAvatar => {
  const id = `${style}-${gender === 'male' ? 'm' : 'f'}-${age}`;
  return { id, name, style, gender, age, preview_url: `/avatars/${id}.png` };
};

/** The twelve built-in hosts; used for names and pictures until the server's list arrives. */
export const BUILTIN_HOSTS: BuiltinAvatar[] = [
  person('toon', 'male', 'young', 'Dara'),
  person('toon', 'female', 'young', 'Sophea'),
  person('toon', 'male', 'adult', 'Vuthy'),
  person('toon', 'female', 'adult', 'Chenda'),
  person('toon', 'male', 'old', 'Ta Sok'),
  person('toon', 'female', 'old', 'Yeay Sarun'),
  person('real', 'male', 'young', 'Rithy'),
  person('real', 'female', 'young', 'Maly'),
  person('real', 'male', 'adult', 'Samnang'),
  person('real', 'female', 'adult', 'Bopha'),
  person('real', 'male', 'old', 'Lok Sen'),
  person('real', 'female', 'old', 'Daun Pen')
];

export const hosts = $state<{
  catalog: AvatarCatalog | null;
  loading: boolean;
  error: unknown;
}>({ catalog: null, loading: false, error: null });

let inflight: Promise<void> | null = null;

/** Loads the catalogue once; `force` fetches it again (after an upload, say). */
export function loadHosts(force = false): Promise<void> {
  if (hosts.catalog && !force) return Promise.resolve();
  if (inflight) return inflight;
  hosts.loading = true;
  inflight = api
    .avatars()
    .then((c) => {
      hosts.catalog = c;
      hosts.error = null;
    })
    .catch((e) => {
      hosts.error = e;
    })
    .finally(() => {
      hosts.loading = false;
      inflight = null;
    });
  return inflight;
}

export const builtinHosts = (): BuiltinAvatar[] => hosts.catalog?.builtin ?? BUILTIN_HOSTS;
export const customHosts = (): CustomAvatar[] => hosts.catalog?.custom ?? [];
export const hostPrefs = (): AvatarPreferences => hosts.catalog?.preferences ?? { default: null, auto: true };

export function setHostPrefs(preferences: AvatarPreferences): void {
  if (hosts.catalog) hosts.catalog.preferences = preferences;
}

export type HostInfo = { id: string; name: string; image: string; custom: boolean };

/** Name and picture for any host id (built-in or `custom:<uuid>`); null when unknown. */
export function hostInfo(id: string | null | undefined): HostInfo | null {
  if (!id) return null;
  if (id.startsWith('custom:')) {
    const c = customHosts().find((x) => x.id === id);
    return c ? { id, name: c.name, image: c.image_url, custom: true } : null;
  }
  const b = builtinHosts().find((x) => x.id === id) ?? BUILTIN_HOSTS.find((x) => x.id === id);
  return b ? { id, name: b.name, image: b.preview_url, custom: false } : null;
}

// ---- what "automatic" means ---------------------------------------------------------
/** Cartoon for story, social and creator videos; realistic for product demos and explainers. */
export const styleFor = (purpose: string): AvatarStyle =>
  purpose === 'product_demo' || purpose === 'explainer' ? 'real' : 'toon';

/** The host a video type uses when nothing is chosen (the same table as the backend's `resolve_avatar`). */
const TYPE_DEFAULT: Record<string, string> = {
  story: 'toon-m-young',
  social_post: 'toon-f-young',
  creator: 'toon-m-adult',
  product_demo: 'real-f-adult',
  explainer: 'real-m-adult'
};

/**
 * The host a new video will get for `purpose`, from the favourite and its `auto` flag:
 * a custom favourite is always used; a built-in one keeps its person (gender and age) and,
 * with `auto`, takes the style that suits the video type; no favourite means the type's default.
 */
export function effectiveHost(purpose: string, prefs: AvatarPreferences): string {
  const fav = prefs.default;
  if (fav && fav.startsWith('custom:')) return fav;
  if (fav) {
    const [, g, a] = fav.split('-');
    return prefs.auto && g && a ? `${styleFor(purpose)}-${g}-${a}` : fav;
  }
  return TYPE_DEFAULT[purpose] ?? 'toon-m-young';
}

/** What the renderer needs to draw host `id`: a built-in avatar or the user's own photo. */
export function avatarPayload(id: string): {
  kind: 'builtin' | 'photo';
  id: string;
  imageUrl: string | null;
  mode: 'mouth' | 'subtle';
} {
  const custom = customHosts().find((c) => c.id === id);
  return custom
    ? { kind: 'photo', id, imageUrl: custom.image_url, mode: custom.mode }
    : { kind: 'builtin', id, imageUrl: null, mode: 'mouth' };
}
