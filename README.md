# AI Video Studio

An AI video **composer**: type a prompt, and the system writes a script, splits it
into scenes, generates a visual and narration per scene, builds timed captions and
a timeline, then renders a final MP4 you can preview, edit scene by scene, and
download.

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

## Architecture

Three runtimes (API, worker, renderer) plus a SvelteKit frontend and three
infrastructure services:

```
                    ┌──────────────────────────┐
  Browser  ───────▶ │  frontend (SvelteKit 2)  │   :5173 dev / :5174 docker
                    │  dashboard + video editor│
                    └───────────┬──────────────┘
                                │  /api/*  (JSON over HTTP)
                    ┌───────────▼──────────────┐
                    │  backend (FastAPI)       │   :8000 dev / :8010 docker
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
                  → TTSProvider   → bytes → S3 → Asset row
                  → scene duration grown to fit the audio
                  → captions re-timed against the real audio length

POST /api/projects/{id}/render
  → RenderJob(queued) + Redis job → 202 {"job_id": ..., "status": "queued"}

worker: builds a normalised composition payload (no DB access in the renderer)
      → Remotion renders frames → FFmpeg encodes H.264/AAC
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
│           └── components/
│               ├── editor/         VideoEditor, VideoPreview, SceneList, SceneCard,
│               │                   PropertiesPanel, CaptionEditor, Timeline,
│               │                   TimelineTrack, TimelineClip, ExportDialog
│               ├── projects/       ProjectCard, PromptDialog
│               └── ui/             Button, Field, StatusBadge, ErrorBanner
├── renderer/                   Remotion 4 composition + headless render CLI
│   └── src/
│       ├── Root.tsx                composition registration + calculateMetadata
│       ├── VideoComposition.tsx    scenes laid onto the timeline
│       ├── scenes/SceneView.tsx    one scene (image, Ken Burns, title, audio)
│       ├── components/CaptionOverlay.tsx
│       ├── schema.ts               zod contract for the render payload
│       └── render.ts               the CLI the worker shells out to
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
`8010`, frontend `5174`.

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
| `LLM_PROVIDER` | `mock` or `openrouter` |
| `OPENROUTER_API_KEY` / `OPENROUTER_MODEL` | real script generation |
| `TTS_PROVIDER` | `edge` = real speech (no key, has Khmer) or `mock` = silence |
| `TTS_RATE` / `TTS_VOLUME` | narration prosody, e.g. `-10%` to slow it down |
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
