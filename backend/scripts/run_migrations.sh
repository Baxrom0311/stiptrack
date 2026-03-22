#!/usr/bin/env sh
set -eu

if [ -x "./.venv/bin/alembic" ]; then
  ALEMBIC_BIN="./.venv/bin/alembic"
else
  ALEMBIC_BIN="alembic"
fi

if ! "$ALEMBIC_BIN" upgrade head; then
  echo "Migration failed. Tekshiring: backend/.env ichidagi DATABASE_URL va ishlayotgan Postgres credentiallari mos bo'lsin." >&2
  exit 1
fi
