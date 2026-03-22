from __future__ import annotations

import asyncio
import sys

from app.services.file_service import ensure_bucket_exists, ensure_bucket_policy


async def _main() -> int:
    bucket_ok = await ensure_bucket_exists()
    if not bucket_ok:
        print("MinIO bucket initialization failed", file=sys.stderr)
        return 1

    policy_ok = await ensure_bucket_policy()
    if not policy_ok:
        print("MinIO bucket policy apply failed", file=sys.stderr)
        return 1

    print("MinIO bucket policy is synchronized")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
