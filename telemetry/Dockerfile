FROM python:3.13-slim

RUN pip install --no-cache-dir uv
WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
# Run from the venv exactly as built: no re-sync (and no network) at container start.
ENV UV_NO_SYNC=1 PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1

COPY app app
COPY auth auth
COPY alembic alembic
COPY alembic.ini main.py ./

RUN useradd --create-home --uid 10002 appuser && chown -R appuser /app
USER appuser
EXPOSE 8000

# Migrations run at start so a fresh volume is usable immediately.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
