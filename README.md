# Stiptrack

Stiptrack is a university internal scholarship platform scaffold.

## Stack
- Backend: FastAPI, SQLAlchemy async, Alembic, Celery, Redis, MinIO
- Frontend: Next.js 14 (App Router), React Query, Zustand, shadcn/ui
- AI Layer: FastMCP server scaffold

## Project Structure
- `backend/` FastAPI service, DB models, Alembic, workers, MCP
- `frontend/` Next.js app with role-oriented routes and UI foundation
- `docker-compose.yml` local development stack

## Quick Start (Docker)
1. Copy env files:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```
2. Start services:
```bash
docker compose up --build
```
3. Apply DB migration:
```bash
docker compose exec backend alembic upgrade head
```
4. Open:
- Frontend: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/api/v1/health`
- MinIO console: `http://localhost:9001`

## Production Baseline
1. Prepare env files:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```
2. Review production-facing values:
- `MINIO_PUBLIC_ENDPOINT`
- `MINIO_PUBLIC_PATH_PREFIX`
- `MINIO_PUBLIC_READ_PREFIXES`
- `NEXT_PUBLIC_API_URL`
- `GUNICORN_WORKERS`
3. Validate compose:
```bash
docker compose -f docker-compose.prod.yml config
```
4. Start production stack:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Notes:
- Production compose does not use dev bind mounts.
- Backend entrypoint runs `alembic upgrade head` automatically only for the backend service.
- Frontend runs `next build` standalone output and serves with `next start` runtime.
- Public entrypoint is `http://<host>:80` via `nginx`.
- In reverse-proxy mode use `NEXT_PUBLIC_API_URL=/api/v1`.
- For presigned MinIO downloads behind `nginx`, set `MINIO_PUBLIC_ENDPOINT=<host>` and `MINIO_PUBLIC_PATH_PREFIX=/files`.
- Keep `MINIO_PUBLIC_READ_PREFIXES=[]` by default. Only open explicit folders such as `["nizom"]` if anonymous read is intentionally required.

## Local Development (without Docker)
### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
./scripts/run_migrations.sh
uvicorn app.main:app --reload
```

Local note:
- `backend/.env.example` host mashinadan ishga tushirish uchun `localhost` qiymatlari bilan berilgan.
- `docker-compose.yml` va `docker-compose.prod.yml` container ichida kerakli `db` / `redis` / `minio` hostlarini avtomatik override qiladi.
- Agar lokal Postgres boshqa credential bilan ishlayotgan bo'lsa, `backend/.env` dagi `DATABASE_URL` ni moslang yoki avval `docker compose up -d db` bilan compose DB ni ishga tushiring.

### Frontend
```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

## Sprint 0 Progress
- Backend scaffold and settings
- Async DB setup + full initial schema models
- Alembic async environment + initial migration
- Redis, MinIO, Celery wiring
- `/api/v1/health` endpoint (DB + Redis + MinIO checks)
- Next.js scaffold + base providers/store/middleware
- Dockerfiles + docker-compose + env examples
