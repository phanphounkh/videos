/** Hands what someone typed on the Home page to the Create page, without putting their
 * prompt in the address bar. Read once, then forgotten. */

const KEY = 'sorya.draft';

export interface Draft {
  prompt: string;
  purpose?: string;
  aspect?: string;
  duration?: number;
}

export function saveDraft(draft: Draft): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify(draft));
  } catch {
    // Without storage the Create page just starts empty.
  }
}

export function takeDraft(): Draft | null {
  try {
    const raw = sessionStorage.getItem(KEY);
    sessionStorage.removeItem(KEY);
    return raw ? (JSON.parse(raw) as Draft) : null;
  } catch {
    return null;
  }
}
