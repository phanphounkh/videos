# =============================================================================
# Renderer-worker image: Python (ARQ tasks) + Node 20 (Remotion) + FFmpeg.
#
# WHY one image instead of two containers: a render job IS a Python task that
# shells out to the Remotion CLI and then uploads the MP4. Splitting them would
# mean shipping the composition payload and the finished file over a network
# boundary for no benefit at this scale.
#
# Build context is the REPO ROOT (see docker-compose.yml) because this image
# needs both ./backend and ./renderer.
# =============================================================================

FROM node:20-bookworm-slim AS renderer-deps

WORKDIR /renderer
COPY renderer/package.json renderer/package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY renderer/ ./


FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:/usr/local/node/bin:$PATH" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    RENDERER_DIR=/renderer \
    REMOTION_DISABLE_TELEMETRY=1

# System packages:
#   ffmpeg                  - encoding/concat/audio normalisation
#   fontconfig, fonts-*     - Latin AND KHMER glyphs inside headless Chromium.
#                             Khmer comes from fonts-noto-core (NotoSansKhmer)
#                             plus fonts-khmeros (the Khmer OS family). NOTE:
#                             there is no `fonts-noto-khmer` package on Debian
#                             bookworm - asking for it fails the whole build.
#                             Without these, every Khmer caption renders as
#                             empty boxes in the final MP4.
#   lib* / chromium deps    - headless Chromium needs these shared libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
      ffmpeg ca-certificates curl \
      fontconfig fonts-noto-core fonts-khmeros fonts-noto-color-emoji \
      libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
      libxcomposite1 libxdamage1 libxfixes3 libxrandr2 libgbm1 libpango-1.0-0 \
      libcairo2 libasound2 libatspi2.0-0 libxshmfence1 \
 && fc-cache -f \
 && fc-list :lang=km family | head -3 \
 && rm -rf /var/lib/apt/lists/*

# Node runtime, copied from the official image (no NodeSource repo needed).
COPY --from=node:20-bookworm-slim /usr/local/bin/node /usr/local/bin/node
COPY --from=node:20-bookworm-slim /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
 && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
 && node --version && npm --version

# Python dependencies
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/app/.venv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --locked --no-dev

# Renderer (with its node_modules) and backend source
COPY --from=renderer-deps /renderer /renderer
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY backend/alembic ./alembic

# Download the exact Chromium build Remotion expects, at build time, so the
# first render does not pay for it (and does not fail if the host is offline).
RUN cd /renderer && npx remotion browser ensure || \
    echo "[warn] chromium not pre-fetched; the first render will download it"

# ARQ worker. Runs as root because Chromium's sandbox needs either root with
# --no-sandbox (what Remotion does in containers) or extra kernel capabilities.
CMD ["arq", "app.workers.main.WorkerSettings"]
