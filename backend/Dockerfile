# =============================================================================
# Backend image: FastAPI served by uvicorn.
#
# Two stages so the runtime image contains no build tooling:
#   builder  - resolves and installs dependencies into /app/.venv with uv
#   runtime  - copies that venv + the source, runs as a non-root user
# =============================================================================

FROM python:3.13-slim AS builder

# uv: fast, lockfile-driven Python dependency management.
COPY --from=ghcr.io/astral-sh/uv:0.12.10 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

# Copy only the dependency manifests first: this layer is cached and only
# invalidated when dependencies actually change, not on every code edit.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev


FROM python:3.13-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

# curl for container-level debugging; ffmpeg for audio probing/duration reads.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ffmpeg \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser

WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser alembic.ini ./alembic.ini
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser app ./app

USER appuser
EXPOSE 8000

# Migrations run from the entrypoint so a fresh volume is usable immediately.
# chmod is explicit: COPY preserves the host file mode, and a script checked out
# without the executable bit fails at container start with "permission denied".
COPY --chown=appuser:appuser docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
