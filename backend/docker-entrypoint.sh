#!/bin/sh
# Applies database migrations, then execs whatever command was requested.
# `exec` matters: it makes the app PID 1 so Docker's stop signal reaches it.
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  echo "[entrypoint] applying database migrations..."
  alembic upgrade head
fi

echo "[entrypoint] starting: $*"
exec "$@"
