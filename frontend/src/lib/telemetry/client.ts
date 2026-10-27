/**
 * Browser telemetry: everything that happens in the browser, sent to the telemetry
 * service (through the same-origin proxy at /api/telemetry, never directly).
 *
 * What is captured, automatically: page views and time on page, clicks (and rage
 * clicks), scroll depth, form fields changed (never their values), every API call with
 * its request id, console errors, uncaught errors, web vitals, tab visibility and the
 * session itself. The app adds its own events with `track()`.
 *
 * Principles
 *  - It never gets in the way: every call is fire-and-forget and cannot throw into the
 *    app; what cannot be sent is dropped.
 *  - It never reads content: no prompts, narration, captions, file names, input values
 *    or emails. Click labels come from fixed UI text only, and anything inside an element
 *    marked `data-private` is ignored. Emails and tokens are scrubbed (the service
 *    scrubs again).
 *  - Events work before sign-in (the login page, errors on load); when a token exists it
 *    is sent so the service can attribute them. The user id is never taken from here.
 *
 * Each batch is POSTed as { session_id, events: [...] }. The browser's session id and a
 * per-call request id are also sent on API calls, so the server's events for a call can
 * be matched to the click that caused it.
 */

type Props = Record<string, string | number | boolean | null | undefined>;
type Level = "debug" | "info" | "warning" | "error";

interface Pending {
  name: string;
  level: Level;
  ts: number;
  duration_ms?: number;
  request_id?: string;
  path: string;
  properties: Props;
}

const TOKEN_KEY = "avs.token";
const SESSION_KEY = "sorya.session";
const ACTIVE_KEY = "sorya.session.active";
const ENDPOINT = "/api/telemetry/ingest/events";
const FLUSH_MS = 4_000;
const BATCH = 25;
const QUEUE_LIMIT = 500;
const SESSION_IDLE_MS = 30 * 60_000;
// A runaway loop must not become a flood.
const EVENTS_PER_MINUTE = 240;
const ERRORS_PER_MINUTE = 20;

let queue: Pending[] = [];
let timer: ReturnType<typeof setTimeout> | undefined;
let sessionId: string | undefined;
let backoffUntil = 0;
let window_: number[] = [];
let errorWindow: number[] = [];
const recentMessages = new Map<string, number>();
let enabled = true;

const getToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

// ----------------------------------------------------------------- scrubbing
const EMAIL =
  /[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}/g;
const SECRET =
  /(?:eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]*|Bearer\s+[A-Za-z0-9._~+/=-]{8,})/g;

/** Emails and credentials never leave the browser. */
export const scrub = (text: string): string =>
  text.replace(EMAIL, "[email]").replace(SECRET, "[token]");

/** `/projects/3f2a…` -> `/projects/:id`, so paths never identify a person's project. */
export const normalisePath = (path: string): string =>
  path
    .split("?")[0]
    .split("#")[0]
    .replace(
      /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi,
      ":id",
    )
    .replace(/\/\d+(?=\/|$)/g, "/:id");

const uuid = (): string => {
  try {
    if (crypto.randomUUID) return crypto.randomUUID();
  } catch {
    // fall through
  }
  const hex = (n: number) =>
    Array.from({ length: n }, () =>
      Math.floor(Math.random() * 16).toString(16),
    ).join("");
  return `${hex(8)}-${hex(4)}-4${hex(3)}-a${hex(3)}-${hex(12)}`;
};

/** An id for one API call: sent as X-Request-ID and recorded on both ends. */
export const newRequestId = (): string => uuid().replace(/-/g, "");

// ------------------------------------------------------------------ settings
export const telemetryEnabled = (): boolean => enabled;

export function setTelemetryEnabled(on: boolean): void {
  enabled = on;
  if (!on) queue = [];
}

// ------------------------------------------------------------------- session
/** One id per tab; a new one after 30 minutes idle, like an analytics "visit". */
export function session(): string {
  const now = Date.now();
  try {
    const last = Number(sessionStorage.getItem(ACTIVE_KEY) ?? 0);
    if (!sessionId)
      sessionId = sessionStorage.getItem(SESSION_KEY) ?? undefined;
    if (sessionId && last && now - last > SESSION_IDLE_MS) {
      sessionId = undefined;
      sessionStarted = false;
    }
    if (!sessionId) {
      sessionId = uuid();
      sessionStorage.setItem(SESSION_KEY, sessionId);
    }
    sessionStorage.setItem(ACTIVE_KEY, String(now));
  } catch {
    sessionId ??= uuid();
  }
  return sessionId;
}

// ------------------------------------------------------------------- sending
function schedule(): void {
  if (timer !== undefined) return;
  timer = setTimeout(() => {
    timer = undefined;
    void flush();
  }, FLUSH_MS);
}

/** Sends what is queued. `keepalive` lets it finish while the page is closing. */
export async function flush(): Promise<void> {
  if (!queue.length || !enabled || Date.now() < backoffUntil) return;
  const batch = queue.splice(0, 100);
  const token = getToken();
  try {
    const response = await fetch(ENDPOINT, {
      method: "POST",
      keepalive: true,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ session_id: session(), events: batch }),
    });
    // Too many events: stop for a while rather than hammer.
    if (response.status === 429) backoffUntil = Date.now() + 60_000;
    // An expired token is not a reason to lose the events: resend them anonymously.
    else if (response.status === 401 && token) {
      queue.unshift(...batch);
      backoffUntil = Date.now() + 5_000;
    }
  } catch {
    // Offline or the service is down: telemetry is best effort, so drop the batch.
  }
  if (queue.length) schedule();
}

function currentPath(): string {
  try {
    return normalisePath(location.pathname);
  } catch {
    return "";
  }
}

function enqueue(
  event: Omit<Pending, "ts" | "path"> & { path?: string; ts?: number },
): void {
  try {
    if (!enabled || typeof window === "undefined") return;
    const now = Date.now();
    window_ = window_.filter((t) => now - t < 60_000);
    if (window_.length >= EVENTS_PER_MINUTE) return;
    window_.push(now);
    session(); // keeps the idle clock honest
    startSession();
    if (queue.length >= QUEUE_LIMIT) queue.shift();
    queue.push({
      ...event,
      ts: event.ts ?? now,
      path: event.path ?? currentPath(),
    });
    if (queue.length >= BATCH) void flush();
    else schedule();
  } catch {
    // never throw into the app
  }
}

const clean = (props?: Props): Props => {
  const out: Props = {};
  for (const [key, value] of Object.entries(props ?? {})) {
    if (value === undefined) continue;
    out[key] = typeof value === "string" ? scrub(value).slice(0, 500) : value;
  }
  return out;
};

// ------------------------------------------------------------------ public API
/** Something the person did, e.g. track('editor.split', { scenes: 4 }). */
export function track(
  name: string,
  props?: Props,
  projectId?: string | null,
): void {
  enqueue({
    name: name.toLowerCase(),
    level: "info",
    properties: clean({ ...props, project_id: projectId ?? undefined }),
  });
}

/** How long something took, or how well it ran. */
export function measure(
  name: string,
  data: {
    duration_ms?: number;
    value?: number;
    props?: Props;
    project_id?: string | null;
  },
): void {
  enqueue({
    name: name.toLowerCase(),
    level: "info",
    duration_ms:
      data.duration_ms === undefined
        ? undefined
        : Math.max(0, Math.round(data.duration_ms)),
    properties: clean({
      ...data.props,
      value: data.value,
      project_id: data.project_id ?? undefined,
    }),
  });
}

/** Something broke. */
export function reportError(
  name:
    | "js.error"
    | "js.unhandledrejection"
    | "api.error"
    | "preview.error"
    | "console.error",
  error: unknown,
  props: Props = {},
): void {
  try {
    const now = Date.now();
    errorWindow = errorWindow.filter((t) => now - t < 60_000);
    if (errorWindow.length >= ERRORS_PER_MINUTE) return;

    const message = scrub(
      error instanceof Error ? error.message : String(error ?? "unknown"),
    );
    // The same error repeating in a loop is reported once a minute.
    const key = `${name}|${message.slice(0, 120)}`;
    if (now - (recentMessages.get(key) ?? 0) < 60_000) return;
    recentMessages.set(key, now);
    if (recentMessages.size > 100) recentMessages.clear();
    errorWindow.push(now);

    enqueue({
      name,
      level: "error",
      properties: clean({
        message: message.slice(0, 300),
        stack:
          error instanceof Error ? scrub(error.stack ?? "").slice(0, 2000) : "",
        ...props,
      }),
    });
  } catch {
    // never throw into the app
  }
}

/** One API call, as seen by the browser. The server records its side under the same id. */
export function reportRequest(call: {
  method: string;
  path: string;
  status: number;
  duration_ms: number;
  request_id: string;
  error?: string;
}): void {
  // Telemetry's own uploads would otherwise be most of what it reports.
  if (call.path.startsWith("/telemetry")) return;
  const failed = call.status === 0 || call.status >= 400;
  enqueue({
    name: "network_request",
    level:
      call.status === 0 || call.status >= 500
        ? "error"
        : failed
          ? "warning"
          : "info",
    duration_ms: Math.round(call.duration_ms),
    request_id: call.request_id,
    properties: clean({
      method: call.method,
      api_path: normalisePath(call.path),
      status_code: call.status,
      error: call.error,
    }),
  });
}

// --------------------------------------------------------------------- pages
let pageStarted = 0;
let pageMaxScroll = 0;
let scrollMarks = new Set<number>();
let pageClicks = 0;

/** Called on every navigation by the root layout. */
export function pageView(): void {
  endPage();
  pageStarted = performance.now();
  pageMaxScroll = 0;
  pageClicks = 0;
  scrollMarks = new Set();
  enqueue({
    name: "page_view",
    level: "info",
    properties: clean({
      referrer: document.referrer
        ? normalisePath(new URL(document.referrer, location.href).pathname)
        : "",
      width: window.innerWidth,
      height: window.innerHeight,
    }),
  });
}

function endPage(): void {
  if (!pageStarted) return;
  enqueue({
    name: "page_leave",
    level: "info",
    duration_ms: performance.now() - pageStarted,
    properties: { max_scroll_pct: pageMaxScroll, clicks: pageClicks },
  });
  pageStarted = 0;
}

let sessionStarted = false;
function startSession(): void {
  if (sessionStarted) return;
  sessionStarted = true;
  queue.push({
    name: "session_start",
    level: "info",
    ts: Date.now(),
    path: currentPath(),
    properties: clean({
      language: navigator.language,
      screen: `${screen.width}x${screen.height}`,
      viewport: `${window.innerWidth}x${window.innerHeight}`,
      dpr: window.devicePixelRatio,
    }),
  });
}

// ------------------------------------------------------------- DOM capture
const INTERACTIVE =
  "a,button,[role=button],[role=tab],[role=menuitem],input[type=submit],summary,[data-track]";

/** A label for what was clicked, from fixed UI text only. Never user content. */
function labelFor(el: Element): string {
  if (el.closest("[data-private]")) return "";
  const explicit =
    el.getAttribute("data-track") ??
    el.getAttribute("aria-label") ??
    el.getAttribute("title");
  if (explicit) return scrub(explicit).slice(0, 60);
  if (el instanceof HTMLAnchorElement) {
    // A link's text is often a project title: use where it goes instead.
    try {
      return `→ ${normalisePath(new URL(el.href, location.href).pathname)}`;
    } catch {
      return "";
    }
  }
  if (el.querySelector("[data-private]")) return "";
  const text = (el.textContent ?? "").trim().replace(/\s+/g, " ");
  return text.length > 0 && text.length <= 30 ? scrub(text) : "";
}

const recentClicks: { x: number; y: number; t: number }[] = [];

function onClick(event: MouseEvent): void {
  const target = event.target instanceof Element ? event.target : null;
  if (!target) return;
  pageClicks += 1;
  const interactive = target.closest(INTERACTIVE);
  const el = interactive ?? target;
  const props = clean({
    tag: el.tagName.toLowerCase(),
    // Only controls are labelled; text in a table cell or paragraph is content.
    label: interactive ? labelFor(interactive) : '',
    x: Math.round(event.clientX),
    y: Math.round(event.clientY),
    interactive: interactive !== null,
  });
  enqueue({ name: "click", level: "info", properties: props });

  // Rage: 3+ clicks within 700ms and 40px of each other.
  const now = Date.now();
  recentClicks.push({ x: event.clientX, y: event.clientY, t: now });
  while (recentClicks.length && now - recentClicks[0].t > 700)
    recentClicks.shift();
  const near = recentClicks.filter(
    (c) => Math.hypot(c.x - event.clientX, c.y - event.clientY) < 40,
  );
  if (near.length >= 3) {
    recentClicks.length = 0;
    enqueue({ name: "rage_click", level: "warning", properties: props });
  }
}

function onChange(event: Event): void {
  const el = event.target;
  if (!(
    el instanceof HTMLInputElement ||
    el instanceof HTMLSelectElement ||
    el instanceof HTMLTextAreaElement
  ))
    return;
  if (el.closest("[data-private]")) return;
  const type =
    el instanceof HTMLInputElement ? el.type : el.tagName.toLowerCase();
  enqueue({
    name: "input_change",
    level: "info",
    // The field, never what was typed. Length only, and not for passwords.
    properties: clean({
      field: el.name || el.id || el.getAttribute("aria-label") || "",
      type,
      length: type === "password" ? undefined : (el.value ?? "").length,
    }),
  });
}

function onSubmit(event: SubmitEvent): void {
  const form = event.target;
  if (!(form instanceof HTMLFormElement)) return;
  enqueue({
    name: "form_submit",
    level: "info",
    properties: clean({
      form:
        form.getAttribute("aria-label") ||
        form.id ||
        form.getAttribute("action") ||
        "",
    }),
  });
}

let scrollTimer: ReturnType<typeof setTimeout> | undefined;
function onScroll(): void {
  if (scrollTimer) return;
  scrollTimer = setTimeout(() => {
    scrollTimer = undefined;
    const doc = document.documentElement;
    const max = doc.scrollHeight - window.innerHeight;
    if (max <= 0) return;
    const pct = Math.min(100, Math.round((window.scrollY / max) * 100));
    pageMaxScroll = Math.max(pageMaxScroll, pct);
    for (const mark of [25, 50, 75, 100]) {
      if (pct >= mark && !scrollMarks.has(mark)) {
        scrollMarks.add(mark);
        enqueue({
          name: "scroll_depth",
          level: "info",
          properties: { depth: mark },
        });
      }
    }
  }, 250);
}

// ------------------------------------------------------------- global capture
let started = false;

/** Installs every capture hook. Call once, as early as possible. */
export function startTelemetry(): void {
  if (started || typeof window === "undefined") return;
  started = true;

  window.addEventListener("error", (event) => {
    // Resource load failures bubble as plain Events with no message; skip those.
    if (event.error || event.message) {
      reportError("js.error", event.error ?? event.message, {
        source: `${
          normalisePath(event.filename ?? "")
            .split("/")
            .pop() ?? ""
        }:${event.lineno ?? 0}`,
      });
    }
  });
  window.addEventListener("unhandledrejection", (event) =>
    reportError("js.unhandledrejection", event.reason),
  );

  // console.error is how most handled failures surface; keep the original behaviour.
  const original = console.error.bind(console);
  console.error = (...args: unknown[]) => {
    original(...args);
    reportError(
      "console.error",
      args
        .map((a) =>
          a instanceof Error ? a.message : typeof a === "string" ? a : "",
        )
        .filter(Boolean)
        .join(" ") || "console.error",
    );
  };

  document.addEventListener("click", onClick, { capture: true, passive: true });
  document.addEventListener("change", onChange, {
    capture: true,
    passive: true,
  });
  document.addEventListener("submit", onSubmit, {
    capture: true,
    passive: true,
  });
  window.addEventListener("scroll", onScroll, { passive: true });

  observeVitals();

  document.addEventListener("visibilitychange", () => {
    enqueue({
      name: "visibility",
      level: "info",
      properties: { state: document.visibilityState },
    });
    if (document.visibilityState === "hidden") {
      emitVitals();
      void flush();
    }
  });
  window.addEventListener("pagehide", () => {
    endPage();
    emitVitals();
    enqueue({ name: "session_end", level: "info", properties: {} });
    void flush();
  });
  window.addEventListener("online", () =>
    enqueue({ name: "network_online", level: "info", properties: {} }),
  );
  window.addEventListener("offline", () =>
    enqueue({ name: "network_offline", level: "warning", properties: {} }),
  );
}

// ----------------------------------------------------------------- web vitals
const vitals: Record<string, number> = {};
let cls = 0;
let longTasks = 0;
let vitalsSent = false;

function observeVitals(): void {
  const watch = (type: string, handle: (entry: PerformanceEntry) => void) => {
    try {
      new PerformanceObserver((list) =>
        list.getEntries().forEach(handle),
      ).observe({ type, buffered: true });
    } catch {
      // This browser does not report it; that is fine.
    }
  };
  watch("largest-contentful-paint", (entry) => (vitals.LCP = entry.startTime));
  watch("paint", (entry) => {
    if (entry.name === "first-contentful-paint") vitals.FCP = entry.startTime;
  });
  watch("layout-shift", (entry) => {
    const shift = entry as PerformanceEntry & {
      value: number;
      hadRecentInput: boolean;
    };
    if (!shift.hadRecentInput) cls += shift.value;
  });
  watch("event", (entry) => {
    // Interaction to Next Paint, approximated by the slowest interaction seen.
    const e = entry as PerformanceEntry & { interactionId?: number };
    if (e.interactionId) vitals.INP = Math.max(vitals.INP ?? 0, entry.duration);
  });
  watch("longtask", (entry) => {
    // Only the painful ones, and a few per page, so it stays a signal.
    if (entry.duration >= 200 && longTasks < 10) {
      longTasks += 1;
      enqueue({
        name: "long_task",
        level: "warning",
        duration_ms: entry.duration,
        properties: {},
      });
    }
  });
  try {
    const nav = performance.getEntriesByType("navigation")[0] as
      PerformanceNavigationTiming | undefined;
    if (nav) vitals.TTFB = nav.responseStart;
  } catch {
    // ignore
  }
}

function emitVitals(): void {
  if (vitalsSent) return;
  vitalsSent = true;
  const all = { ...vitals, CLS: Math.round(cls * 1000) / 1000 };
  for (const [metric, value] of Object.entries(all)) {
    enqueue({
      name: "web_vital",
      level: "info",
      properties: { metric, value: Math.round(value * 1000) / 1000 },
    });
  }
}

/** Test hook: forget everything. */
export function _resetForTests(): void {
  queue = [];
  timer = undefined;
  backoffUntil = 0;
  errorWindow = [];
  window_ = [];
  recentMessages.clear();
  enabled = true;
}

export const _queued = (): number => queue.length;
