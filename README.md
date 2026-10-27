# Sorya

An AI video **composer** for product demos, social media posts, creator videos,
explainers and stories: pick a purpose, type a prompt, and the system writes a
script, splits it into scenes, generates a visual and narration per scene, builds
timed captions and a timeline, then renders a final MP4 you can preview, edit scene
by scene, and download.

Built Khmer-capable from the ground up: UTF-8 everywhere, language metadata on
project *and* scene, replaceable TTS/STT providers, Khmer-aware caption
segmentation (Khmer has no spaces between words), and Khmer fonts in both the
editor UI and the video renderer.

> **Status: the MVP runs end to end.** Prompt → script → scenes → images →
> narration → captions → timeline → MP4 → download, verified in a browser.
> The LLM, image and TTS providers currently run as **mocks** (see
> [What is real and what is mocked](#what-is-real-and-what-is-mocked)) — switching to
> OpenRouter and real media providers is configuration plus one provider class.

---

## Contents

- [Video purposes](#video-purposes)
- [Architecture](#architecture)
- [End-to-end flow](#end-to-end-flow)
- [Repository layout](#repository-layout)
- [Requirements](#requirements)
- [Setup](#setup)
- [Local development](#local-development)
- [Docker usage](#docker-usage)
- [Database migrations](#database-migrations)
- [Tests](#tests)
- [Environment variables](#environment-variables)
- [API overview](#api-overview)
- [Khmer support](#khmer-support)
- [What is real and what is mocked](#what-is-real-and-what-is-mocked)
- [Troubleshooting](#troubleshooting)

---

## Video purposes

Every project has a **purpose** that decides how the script is written and how the
video looks. The create form loads them from `GET /api/purposes` and preselects
each purpose's aspect ratio, length, style, tone and audience.

| Purpose | Default | Host | Closing button | Script rules |
|---|---|---|---|---|
| `story` | 9:16, 60 s | on | Follow | Hook, twist, payoff; one connected story |
| `product_demo` | 16:9, 60 s | off | "Try it today" | Problem, benefits before features, **no invented features, prices or testimonials** |
| `social_post` | 9:16, 30 s | off | Follow | Scroll-stopping first line, five-second scenes, one ask |
| `creator` | 16:9, 3 min | on | "Subscribe" | First-person voice, segments, pattern interrupts, recap |
| `explainer` | 16:9, 90 s | on | Follow | Simple to detailed, one idea per scene, only established facts |

Per project you can also turn the animated host on or off (`presenter`; with it off
the scene's picture fills the frame and the narration is a voice-over) and set a
custom closing-button label (`cta_text`). The editor has a **Host** toggle.

Adding a purpose is one entry in `backend/app/services/purposes.py` (plus the value
in `VideoPurpose` and the renderer's `purpose` enum); the form, prompts and defaults
follow from it.

---

## Editor

The editor works on the scene model: each scene is a clip on the timeline.

| Do this | How |
|---|---|
| Reorder scenes | drag a clip sideways on the Video track |
| Trim or lengthen | drag a clip's left or right edge |
| Split | move the playhead into a scene and press **S** (narration, captions, voice and an uploaded clip carry on across the cut) |
| Text and stickers | **T Text** / **Sticker** in the toolbar, then drag, resize (corner dot) and rotate (top dot) on the preview; drag or trim their bars on the timeline to set when they appear |
| Your own media | **Media** tab (or ⬆ Media) uploads pictures and clips; HEVC/phone video is converted to H.264 on upload |
| Sound | **Audio** tab: voice volume, a clip's own sound, your own music track (volume, fades, ducking under speech) |
| Captions | **Captions** tab: edit wording and timing, add one at the playhead, delete, or reset to auto. Click a caption bar on the timeline to jump to it. Your edits are kept when you change a scene's length; new narration, language or voice rebuilds them |
| Undo / redo | **Ctrl+Z** / **Ctrl+Shift+Z**; the whole timeline is restored on the server |

Shortcuts: Space play/pause, S split, Delete remove, Ctrl+D duplicate, ←/→ one frame
(Shift: one second), Home/End, +/- zoom, Esc deselect.

Everything the editor adds lives in `scene.settings` (validated in
`backend/app/schemas/scene_settings.py`) and in the project's `music_asset_id` /
`settings.music`, so existing projects keep working and the AI generator is unchanged.
Split and trim are pure arithmetic in `backend/app/services/timeline_ops.py`; undo is
`PUT /api/projects/{id}/scenes/timeline` with a snapshot.

---

## Telemetry

A separate service (`./telemetry`, its own Postgres) that records **every event from the
browser, the API and the render worker**, and an admin panel that shows them.

```
browser ──POST /api/telemetry/ingest/events──▶ web app proxy ──▶ telemetry service ─┐
API + worker ──XADD──▶ Redis stream `sorya:telemetry:events` ──▶ consumer ──────────┴▶ events table
admin panel (/telemetry) ◀── /api/telemetry/* ◀── web app proxy ◀── telemetry service
```

- **Backend and worker** never wait on telemetry: events go to a bounded in-process queue
  and are written to a Redis stream in batches; if Redis or the service is down they are
  dropped and counted, never raised. Every HTTP request becomes an `api_request` event
  (including failed and signed-out ones), every structured log line becomes a `log` event,
  every LLM / voice / image call an `llm_usage` event, and the domain events
  (`project_created`, `script_generated`, `export_started`, `render_job`, ...) are kept.
- **Browser** (`frontend/src/lib/telemetry/client.ts`): page views and time on page, clicks
  and rage clicks, scroll depth, fields changed (never their values), every API call,
  console and uncaught errors, web vitals, tab visibility. It works before sign-in.
  Each API call carries an `X-Request-ID` and the tab's `X-Telemetry-Session`, so one
  click can be followed through to everything the server did for it.
- **Admin panel** (the separate `./admin` app, below): *Events* (every event, filters in the URL,
  facet counts, histogram, live tail, search, export CSV/JSON, expandable detail with the
  other events of the same request), *Sessions* and a session timeline that interleaves
  browser and server events, *Users*, *Overview* (traffic, errors, AI tokens and cost,
  renders, web vitals) and *Health* (database, Redis, consumer, backlog).

## Admin panel (`./admin`)

A separate web app, outside the frontend (dev: `cd admin && npm run dev` on port **5175**;
Docker: the `admin` service, `ADMIN_HOST_PORT`). It has its own sign-in for administrator
accounts and talks to the backend and the telemetry service through its own proxy.

- **Overview, Events, Sessions, Health**: everything telemetry knows (see above).
- **LLM usage**: calls, failure rate, tokens, estimated cost, by model and by person, and the
  latest failures.
- **Users**: search and filter every account; open one to see their usage against limits and
  their activity, and to **disable/enable** them (blocks sign-in and API access at once),
  **grant or revoke admin**, set their **plan and monthly limits** (AI generations, AI tokens,
  exports; empty = unlimited, enforced immediately), reset the month, or **delete** the account
  (typed-email confirmation). You cannot disable, demote or delete yourself, and the last
  active admin is protected. Every change is logged as an event (`admin_user_updated`, ...).

## The app (frontend)

- **Home**: pick a format (Generate with AI, Blank, Social reel, YouTube, Presentation, Import media), a template banner, *Continue editing*, templates by category, and recent activity.
- **Projects**: All / Recent / Starred, folders, grid or list, tick boxes with a bulk bar (Move, Duplicate, Star, Trash), rename, move, and a **Trash** that keeps projects for 30 days (restore, delete forever, empty).
- **Templates**: twelve ready-made starting points in four categories, with thumbnails drawn by the renderer
  (`cd backend && PYTHONPATH=. uv run python scripts/render_template_thumbnails.py` redraws them into `frontend/static/templates`).
- **Create**: a wizard (name, start with, aspect ratio, resolution HD/Full HD, frame rate, folder, and your own media) or **Generate with AI** (`/create/ai`) for the prompt form.
- **Editor**: tool rail (Scenes, Media, Text, Elements, Audio, Captions), properties on the right, transport and safe guides under the preview, and a timeline with per-track lock/eye/volume (eye and volume are preview-only).
- **Sidebar**: Create, Home, Projects, Templates, Trash, Settings and a storage meter (plan default 2 GB free, 20 GB pro, 100 GB team; an admin can override it per person).

## Hosts (avatars)

Every video can have an animated host. There are **12 built-in hosts** in two styles, **cartoon** and
**semi-realistic illustrated**, each as male/female and young/adult/old (Dara, Sophea, Vuthy, Chenda, Ta Sok,
Yeay Sarun; Rithy, Maly, Samnang, Bopha, Lok Sen, Daun Pen), plus **your own uploaded photo** (up to 12), either with
a **talking mouth** drawn over the face or with **subtle motion** (breathing and a voice-reactive glow).

- **Choosing:** a favourite in Settings → Avatar, a host in the Generate with AI form, and *Change host* in the editor.
- **Automatic style:** cartoon for story, social and creator videos, realistic for product demos and explainers.
  A built-in favourite keeps its person (gender and age) and the style follows the video type; turn this off to use it as is.
  An uploaded avatar is always used as is.
- **How it works:** `renderer/src/avatars.ts` (the catalogue), `Host.tsx` (dispatches to the cartoon, realistic or photo host),
  `backend/app/services/avatars.py` (resolution rules and the payload). `cd renderer && npm run render:avatars`
  redraws the picker previews in `frontend/static/avatars`.

## Your account (frontend)

Click the avatar in the navbar: your plan, your latest videos, **Usage** (this month against your
plan's limits), **Settings** (name, password, default language and purpose for new videos,
delete account) and Log out. Hitting a limit shows a clear `QUOTA_EXCEEDED` message.

**Making someone an admin** (no request can do it, and it is never inferred from an
email): `cd backend && uv run python -m app.cli make-admin you@example.com`. The telemetry
service checks admin-ness by asking the backend, so there is one source of truth.

**Run it**: `docker compose up` starts `telemetry-db` and `telemetry` with the rest. For
local development: `cd telemetry && uv run alembic upgrade head && uv run uvicorn main:app
--port 8006` (see `telemetry/.env.example`), with `TELEMETRY_URL` pointing the web app at it.

**Settings**: `TELEMETRY_ENABLED` (backend/worker emit), `TELEMETRY_STREAM_KEY`,
`TELEMETRY_PRICES` (cost is shown only when you give prices, as JSON keyed
`<service>.<provider>`, for example `{"llm.gemini": {"input_per_1m": 0.30,
"output_per_1m": 2.50}}`; no price shows a dash, never a made-up zero). Retention
(90 days by default) and ingest limits are the telemetry service's own settings.

**Privacy.** No prompts, narration, captions, files, input values or emails are recorded.
Click labels come from fixed UI text only (links by their destination, never their text),
anything under `data-private` is ignored (the admin panel is a separate app that records nothing), and emails and
tokens are scrubbed in the browser, in the backend and again on arrival.


---

## Architecture

Three runtimes (API, worker, renderer) plus a SvelteKit frontend and three
infrastructure services:

```
                    ┌──────────────────────────┐
  Browser  ───────▶ │  frontend (SvelteKit 2)  │   :5173 dev / :3355 docker
                    │  dashboard + video editor│
                    └───────────┬──────────────┘
                                │  /api/*  (JSON over HTTP)
                    ┌───────────▼──────────────┐
                    │  backend (FastAPI)       │   :8000 dev / :8011 docker
                    │  routes → services →     │
                    │  repositories → models   │
                    └──┬────────┬──────────┬───┘
                       │        │          │
            ┌──────────▼─┐  ┌───▼────┐  ┌──▼──────────────┐
            │ postgres   │  │ redis  │  │ S3 (SeaweedFS)  │
            │ :5435      │  │ :6381  │  │ :9100           │
            └────────────┘  └───┬────┘  └──▲──────────────┘
                                │ queue    │ media bytes
                    ┌───────────▼──────────┴───┐
                    │  worker (ARQ, Python)    │
                    │  generation + render jobs│
                    └───────────┬──────────────┘
                                │ spawns a process
                    ┌───────────▼──────────────┐
                    │  renderer (Remotion +    │
                    │  FFmpeg) → final MP4     │
                    └──────────────────────────┘
```

**Why this shape**

| Decision | Reason |
|---|---|
| **Modular monolith backend** | One FastAPI app with hard internal boundaries (`api/ → services/ → repositories/ → models/`) is far cheaper to build and debug than microservices, and the boundaries let us split later if scale demands it. |
| **Separate worker** | Script, image, TTS and render work takes seconds to minutes. It must never run inside an HTTP request: the API inserts a job row, pushes to Redis, returns `202`. |
| **Separate renderer process** | Remotion drives headless Chromium and FFmpeg is CPU-bound. As its own process a render cannot take the API down, and the renderer stays a **pure function of its input payload** — it never touches the database. |
| **Provider abstractions** | `LLMProvider`, `ImageProvider`, `TTSProvider`, `STTProvider`, `VideoProvider`. Routes never call OpenRouter; swapping in a Khmer TTS engine touches one file. |
| **ARQ for jobs** | The backend is fully asyncio, so an ARQ task is just an `async def` reusing the same async SQLAlchemy session and `httpx` clients. Celery would force a sync path or a prefork/asyncio bridge; Dramatiq is sync-first. ARQ is the smallest production-ready option here. |
| **SeaweedFS for S3 locally** | MinIO's images are no longer publicly pullable (docker.io and quay.io both require auth). SeaweedFS speaks the same S3 API, so the boto3-based storage layer is unchanged and AWS S3 / R2 / MinIO drop in through `S3_*` env vars. |

### Layers, strictly

```
HTTP route        validates the request, calls a service, returns a schema
  ↓               (no business logic, no SQL)
service           the use case: policy, transactions, logging, orchestration
  ↓
repository        every database query lives here
  ↓
model             SQLAlchemy 2.x typed models
```

AI and storage are reached the same way: `service → provider interface → concrete
provider`, chosen by configuration.

## End-to-end flow

```
POST /api/projects/{id}/generate
  → Pydantic validates the request
  → generation_service → LLMProvider → raw text
                       → parsed + VALIDATED by Pydantic (never trusted raw)
                       → scenes persisted, captions derived from narration
  → media jobs enqueued on Redis
  → 202 {"project_id": ..., "status": "ready", "media_jobs_queued": 8}

worker: per scene → ImageProvider → bytes → S3 → Asset row (key + metadata only)
                  → TTSProvider   → bytes + speech marks → S3 → Asset row
                  → scene duration grown to fit the audio
                  → speech marks + per-frame loudness saved in scene.settings
                  → captions timed to the real speech marks

POST /api/projects/{id}/render
  → RenderJob(queued) + Redis job → 202 {"job_id": ..., "status": "queued"}

worker: builds a normalised composition payload (no DB access in the renderer)
      → Remotion renders frames → FFmpeg encodes H.264/AAC
      → loudness normalised to -14 LUFS (video stream copied)
      → MP4 uploaded to S3, RenderJob → completed
frontend polls GET /api/render-jobs/{id} → {"status":"rendering","progress":67}
      → preview + download
```

## Repository layout

```
vid/
├── backend/                    FastAPI app + ARQ workers (uv-managed, Python 3.13)
│   ├── app/
│   │   ├── main.py                 app factory (thin on purpose)
│   │   ├── api/
│   │   │   ├── dependencies.py     DB session, current user
│   │   │   ├── router.py           every route module is mounted here
│   │   │   └── routes/             health, auth, projects, scenes,
│   │   │                           generation, renders, assets
│   │   ├── core/                   config, logging, exceptions, database, security
│   │   ├── models/                 SQLAlchemy models + enums
│   │   ├── schemas/                Pydantic request/response + presenters
│   │   ├── repositories/           all database queries
│   │   ├── services/
│   │   │   ├── project_service.py  scene_service.py  caption_service.py
│   │   │   ├── generation_service.py  render_service.py  render_payload.py
│   │   │   ├── queue.py            ARQ enqueueing
│   │   │   ├── ai/{llm,image,speech,video}/   provider interfaces + impls
│   │   │   └── storage/            S3 abstraction + key layout + public URLs
│   │   └── workers/                ARQ task definitions + entrypoint
│   ├── alembic/versions/           migrations
│   ├── tests/                      65 pytest tests
│   ├── Dockerfile  docker-entrypoint.sh  pyproject.toml
├── frontend/                   SvelteKit 2 + Svelte 5 runes + Tailwind 4 + TS
│   └── src/
│       ├── routes/                 /login /register /projects /create /projects/[id]
│       └── lib/
│           ├── api/                one HTTP client + typed endpoint wrappers
│           ├── stores/             auth state (runes)
│           ├── types/              API types
│           ├── remotion/           editor preview = the renderer's own composition
│           │                       in @remotion/player (preview matches export)
│           └── components/
│               ├── editor/         VideoEditor, VideoPreview, SceneList, SceneCard,
│               │                   PropertiesPanel, CaptionEditor, Timeline,
│               │                   TimelineTrack, TimelineClip, ExportDialog
│               ├── projects/       ProjectCard, PromptDialog
│               └── ui/             Button, Field, StatusBadge, ErrorBanner
├── renderer/                   Remotion 4 composition + headless render CLI
│   └── src/
│       ├── Root.tsx                composition registration + calculateMetadata
│       ├── VideoComposition.tsx    timeline, ducked music bed, sound effects, progress bar
│       ├── scenes/SceneView.tsx    one scene: layout, camera, transitions, CTA
│       ├── components/             Presenter (lip-synced host), CaptionOverlay (karaoke),
│       │                           Backdrop, Sticker, FollowCta
│       ├── story.ts                story beats, colours, shared sticker/CTA/speech timing
│       ├── schema.ts               zod contract for the render payload
│       └── render.ts               the CLI the worker shells out to
│   ├── public/studio/              generated music bed + sound effects
│   └── scripts/make_audio.py       regenerates them (standard library only)
├── infra/
│   ├── worker.Dockerfile           Python + Node + Chromium + FFmpeg + Khmer fonts
│   └── seaweedfs/s3.json           S3 identities (anonymous read for media)
├── docker-compose.yml              full stack
├── docker-compose.infra.yml        postgres + redis + S3 only (for host dev)
├── .env.example
└── README.md
```

## Requirements

- Debian/Ubuntu Linux
- Python 3.13 + [`uv`](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- FFmpeg (`ffmpeg -version`)
- Docker + Docker Compose v2 (`docker compose version`)
- Khmer fonts on the render host: `sudo apt install fonts-noto-khmer`

## Setup

```bash
cp .env.example .env            # then edit values; JWT_SECRET: openssl rand -hex 32

cd backend  && uv sync      && cd ..
cd frontend && npm install  && cd ..
cd renderer && npm install  && cd ..
```

## Local development

The recommended loop runs **infrastructure in Docker** and **app code on the host**
(instant reload, native debugger, no image rebuilds):

```bash
# 1. infrastructure
docker compose -f docker-compose.infra.yml up -d
docker compose -f docker-compose.infra.yml ps     # all healthy

# 2. migrations
cd backend && uv run alembic upgrade head

# 3. API           → http://localhost:8000/docs
cd backend && uv run uvicorn app.main:app --reload --port 8000

# 4. worker (separate terminal) — generation + render jobs
cd backend && uv run arq app.workers.main.WorkerSettings

# 5. frontend      → http://localhost:5173
cd frontend && npm run dev
```

Then: register → **Create** → type a prompt → Generate → edit scenes → Export.

Optional: `cd renderer && npm run studio` opens Remotion Studio for visual
composition work — see the warning in [Troubleshooting](#troubleshooting).

## Docker usage

```bash
docker compose up -d --build        # everything, including the worker image
docker compose ps
docker compose logs -f backend worker
docker compose down                 # add -v to wipe volumes
```

Host ports are deliberately offset so the stack never collides with other
projects: Postgres `5435`, Redis `6381`, S3 `9100` (console `9101`), backend
`8011`, frontend `3355`.

**Inside** the compose network services reach each other by service name on the
container port — `postgres:5432`, `redis:6379`, `s3:8333`. Never `localhost`:
inside a container that means the container itself. `docker-compose.yml` overrides
the host-oriented URLs from `.env` with these in-network values.

The worker image is large (~2 GB): it carries Python, Node, FFmpeg, headless
Chromium and the Noto Khmer fonts needed to draw Khmer captions into the video.

## Database migrations

```bash
cd backend
uv run alembic upgrade head                              # apply
uv run alembic revision --autogenerate -m "add x to y"   # create
uv run alembic downgrade -1                              # roll back one step
```

Always read a generated migration before applying it: autogenerate cannot see
renames (they look like drop + create, which destroys data). The initial
migration is hand-ordered because the schema has a deliberate reference cycle
(`assets → projects/scenes` and `projects/scenes → assets`), which inline FOREIGN
KEY clauses cannot express; the back-references are added with `ALTER TABLE`.

## Tests

```bash
cd backend && uv run pytest -q        # 65 tests
cd backend && uv run ruff check .
cd frontend && npm run check          # svelte-check + TS
cd renderer && npm run typecheck
cd renderer && npm run render:sample  # proves Remotion + FFmpeg work locally
```

The suite creates a throwaway PostgreSQL database per run, applies the real
Alembic migrations into it (so migrations are tested too), and drops it at the
end. AI providers are replaced with in-memory fakes through the provider
interfaces, so **no test needs an API key, a network or money**.

What is covered: password hashing, JWT auth, account enumeration resistance,
cross-user isolation on every project/scene/render route, project and scene CRUD,
the scene ordering invariant (insert, reorder, delete, duplicate), LLM response
validation (fenced JSON, trailing commas, truncation, missing fields, bad
transitions), Khmer caption segmentation and timing, the generation pipeline with
fake providers, storage key layout and URL construction, upload validation
(MIME allow-list, size cap, filename sanitisation), and render-job lifecycle plus
the composition payload contract.

## Environment variables

Every variable is documented in [`.env.example`](.env.example). Settings are
parsed and type-validated once at startup by `backend/app/core/config.py`, so a
missing or malformed value fails the boot instead of surfacing later as a
mysterious runtime error.

Essentials:

| Variable | Meaning |
|---|---|
| `DATABASE_URL` | async PostgreSQL DSN (`postgresql+asyncpg://…`) |
| `REDIS_URL` | Redis for the ARQ queue |
| `JWT_SECRET` | signing key — **must** be changed outside development |
| `S3_ENDPOINT_URL` | endpoint the **backend** uses (`http://s3:8333` in Docker) |
| `S3_PUBLIC_BASE_URL` | base URL the **browser and renderer** use (`http://localhost:9100`) |
| `LLM_PROVIDER` | `gemini` or `openrouter` for prompt-following stories; `mock` only for offline tests |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | OpenRouter story generation (key required) |
| `GEMINI_API_KEY` | enables Gemini for story, voice and subtitle timing; empty = fall back to OpenRouter/Edge |
| `GEMINI_MODEL` / `GEMINI_TTS_MODEL` | `gemini-3.8-flash` (story + alignment) / `gemini-3.8-flash-tts` (voice) |
| `GEMINI_TTS_VOICE` | presenter voice, any Gemini prebuilt voice (`Puck`, `Kore`, `Charon`...) |
| `GEMINI_REVIEW_SCRIPT` | second Gemini pass that proofreads generated Khmer scripts |
| `TTS_PROVIDER` | `gemini` = Gemini TTS + aligned subtitles, `edge` = real speech (no key, has Khmer), or `mock` = silence |
| `TTS_RATE` / `TTS_VOLUME` | narration prosody; `+10%` by default for brisk short-form pacing, e.g. `-10%` to slow it down |
| `IMAGE_PROVIDER` | `mock` today |
| `REMOTION_CONCURRENCY` | Chromium tabs per render; `1` on a low-memory host |
| `RENDERER_DIR` | path to the Remotion project (`../renderer` on the host, `/renderer` in the worker image) |

Mixing up the two S3 URLs is the classic "works in the API, broken in the
browser" bug: media URLs are built from `S3_PUBLIC_BASE_URL`, and a test asserts
the internal hostname never leaks into them.

## API overview

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health`, `/api/health/ready` | liveness / readiness |
| `POST` | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout` | auth |
| `GET` | `/api/auth/me` | current user |
| `GET/POST` | `/api/projects` | list / create |
| `GET/PATCH/DELETE` | `/api/projects/{id}` | project detail |
| `GET` | `/api/projects/{id}/detail` | project + full scene timeline (one call for the editor) |
| `POST` | `/api/projects/{id}/duplicate` | deep copy |
| `POST` | `/api/projects/{id}/generate` | prompt → script → scenes (+ queue media) |
| `GET/POST` | `/api/projects/{id}/scenes` | list / add |
| `POST` | `/api/projects/{id}/scenes/reorder` | full reorder |
| `GET/PATCH/DELETE` | `/api/scenes/{id}` | one scene |
| `POST` | `/api/scenes/{id}/duplicate` | duplicate a scene |
| `POST` | `/api/scenes/{id}/generate-image` | regenerate the visual |
| `POST` | `/api/scenes/{id}/generate-voice` | regenerate narration (and re-time captions) |
| `POST` | `/api/scenes/{id}/regenerate` | image + voice for one scene only |
| `POST` | `/api/scenes/{id}/captions` | recompute caption segments |
| `POST` | `/api/projects/{id}/render` | enqueue a render → `202 {job_id}` |
| `GET` | `/api/render-jobs/{id}` | status + progress + output URL |
| `POST` | `/api/assets/upload` | upload your own image/video/audio |
| `GET` | `/api/assets/{id}`, `/api/assets/{id}/download-url` | metadata / presigned URL |

Interactive docs: `http://localhost:8000/docs`.

Every error uses one envelope, so the frontend branches on `code`, never on an
English sentence:

```json
{ "error": { "code": "PROJECT_NOT_FOUND", "message": "Project was not found." } }
```

Someone else's project returns `404`, not `403` — a `403` would confirm the id
exists.

## Khmer support

Khmer is not a translation layer bolted on at the end; it changes real logic:

- **No whitespace between words.** `str.split()` on Khmer yields one enormous
  "word", so caption segmentation breaks Khmer on punctuation (`។ ៕ ៖ ,`) and then
  on a character budget, and speech duration is estimated from Khmer **character**
  count rather than word count (`app/services/ai/speech/timing.py`).
- **Gemini path (recommended for Khmer).** The story is written for the one
  animated host, with a mood (drives the host's expression) and a voice
  direction per scene, then proofread by a second Khmer-editor pass. Gemini TTS
  reads each scene with its direction, and Gemini then listens to the audio and
  timestamps each phrase of the exact script; answers that fail validation fall
  back to estimated timing rather than wrong subtitles.
- **Caption timing.** Edge TTS reports one speech mark per space-separated Khmer
  phrase (per word in English). Captions follow those marks; long phrases are
  split on cluster boundaries and share the phrase's time. The karaoke highlight
  splits Khmer into words with `Intl.Segmenter`, never on spaces.
- **Fonts.** Noto Sans Khmer is loaded in the editor UI and installed in the
  worker image; without it Khmer captions render as empty boxes in the MP4.
  Khmer also gets a taller line height in both the UI and the renderer.
- **Visual prompts stay English.** Image models are trained on English, so the
  narration can be Khmer while `visual_prompt` remains ASCII — enforced in the
  provider and covered by a test.
- **Language is stored on project *and* scene**, so a bilingual video is a data
  change, not a schema change.
- **UTF-8 end to end**: database created with `--encoding=UTF8`, `ensure_ascii=False`
  when the render payload is written, UTF-8 locale in every image.

Adding real Khmer narration means writing one `TTSProvider` subclass and
returning it from `get_tts_provider("km")`. Nothing else changes.

## What is real and what is mocked

**Implemented and verified end to end**
- Auth (register/login/me/logout), JWT, bcrypt, per-user authorization on every route
- Project CRUD + duplicate; scene CRUD + insert/reorder/duplicate/delete with a
  dense 1..N ordering invariant
- Prompt → structured script → scene rows, with strict Pydantic validation of the
  model output and defensive JSON repair
- Per-scene image and narration assets stored in S3 (database holds keys only)
- **Real text-to-speech** (`TTS_PROVIDER=edge`): Microsoft Edge neural voices,
  no API key, including Khmer (`km-KH-PisethNeural` / `km-KH-SreymomNeural`).
  Audio duration is MEASURED with ffprobe and the scene length follows it, so
  narration is never clipped at a scene boundary
- Caption segmentation and timing, re-timed against real audio duration
- Redis/ARQ background jobs with per-scene isolation (one failure does not kill a project)
- Remotion + FFmpeg render pipeline with live progress, upload, and a downloadable MP4
- Dashboard, prompt page, and a desktop editor (scene list, preview with playhead
  and audio, properties panel, 4-track timeline, export dialog)
- Uploads with MIME allow-list, size cap and filename sanitisation

**Mocked — clearly labelled in the UI and the API response**
- `LLM_PROVIDER=mock` — a deterministic, schema-valid script built from your
  prompt. It does **not** understand the prompt. The real `OpenRouterLLMProvider`
  is implemented; set `LLM_PROVIDER=openrouter` + `OPENROUTER_API_KEY`.
- `IMAGE_PROVIDER=mock` — draws a real PNG (gradient + prompt text + a
  "placeholder image" label) at the project's exact dimensions. Not an AI image.
- `TTS_PROVIDER=mock` — a silent MP3 of the correct duration, for offline work
  and tests. The default is now `edge`, which produces real speech.

**Not implemented (interfaces exist, deliberately empty)**
- Speech-to-text / forced alignment for word-level caption timing
- Text-to-video and image-to-video providers
- Music track, avatars, lip sync, voice cloning, collaboration, billing

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| **Renders come out entirely black, or Remotion Studio changed my files** | Remotion Studio's visual editing **writes to your source files** and can strip JSX from `SceneView.tsx` / `VideoComposition.tsx` (it once left `return null`). Don't edit compositions through Studio in this project; use it read-only, and `git diff renderer/src` after. A black render with a *white* `remotion still` means the component tree rendered nothing. |
| `uv run alembic …` → `No 'script_location' key found` | You are not in `backend/`, or `alembic.ini` is missing. `cd backend` first. |
| `MissingGreenlet` from SQLAlchemy | A lazy relationship was touched in async code. Load it eagerly (`selectinload`) in the repository instead of `session.refresh(obj, ["rel"])`. |
| `duplicate key value violates "uq_scene_project_number"` | Scene numbers were written in one pass. Ordering must park rows at negative numbers first, then write 1..N (`SceneService._apply_order`). |
| Frontend shows `Failed to fetch` | Backend not running on the port Vite proxies to. Start uvicorn, or set `BACKEND_URL`. |
| Images/audio 404 in the browser but work in the API | `S3_PUBLIC_BASE_URL` points at the internal endpoint. It must be host-reachable (`http://localhost:9100`). |
| Khmer text renders as boxes | Install `fonts-noto-khmer` on the host and rebuild the worker image. |
| `pull access denied for minio/minio` | MinIO images are no longer public. This stack uses SeaweedFS instead; keep `docker-compose.yml` as is. |
| Render job stuck in `queued` | The worker is not running: `cd backend && uv run arq app.workers.main.WorkerSettings`, or `docker compose up -d renderer-worker`. |
| Worker OOM / Chromium crash | Rendering needs ~1–2 GB free. The worker is capped at `max_jobs = 1`; scale with more worker containers, not more concurrency. |
| `Timeout exceeded rendering the component at frame N` | The host is swapping. Keep `REMOTION_CONCURRENCY=1` and raise `REMOTION_FRAME_TIMEOUT_MS`. |
| Narration is silent even though `TTS_PROVIDER=edge` | A **host** `arq` worker is still running and competing for the same Redis queue with its own (stale) config. `pkill -f "arq app.workers"`, then check `docker logs avs_worker` shows the job. |
| Narration gets cut off at a scene boundary | The audio duration was estimated instead of measured. `ffprobe` cannot read MP3 duration from a pipe — `app/services/media.py` must probe a temp file. |
