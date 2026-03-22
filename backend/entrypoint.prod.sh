#!/bin/sh
set -eu

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "Running Alembic migrations..."
  alembic upgrade head

  echo "Applying MinIO bucket policy..."
  python scripts/apply_minio_bucket_policy.py
fi

exec "$@"
