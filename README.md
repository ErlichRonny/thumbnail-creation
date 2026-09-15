# thumbnail-creation

A REST API that accepts image uploads, resizes them into thumbnails (via presets or custom dimensions) asynchronously, and lets clients poll for status and retrieve the result. Built with FastAPI, Postgres (used as both the metadata store and the job queue), and a separate worker process for the actual image processing.

## Architecture

See [docs/architecture.md](docs/architecture.md) for the request lifecycle and data flow diagrams.

## Features

- Upload one or more images in a single request (`POST /images`), resized via a named preset (`small`/`medium`/`large`) or custom width/height, preserving aspect ratio and never upscaling.
- Asynchronous processing: uploads return immediately with `status=pending`; a separate worker (or multiple, for horizontal scaling) does the actual resizing.
- Poll for status and metadata (`GET /images/{id}`), then retrieve the generated file (`GET /images/{id}/file`) once done.
- Concurrency-safe job claiming via Postgres `SELECT ... FOR UPDATE SKIP LOCKED` — verified with a dedicated race-condition test and an end-to-end test firing 20 concurrent uploads against 5 concurrent worker slots.
- Upload validation: magic-byte content sniffing (not just trusting the client's declared content type), file size/count limits, and resize-spec validation.
- Prometheus metrics (`GET /metrics`) and a real health check (`GET /health`, verifies DB connectivity)
- Structured JSON logging across both the API and worker processes.

## Requirements

- Python 3.12+
- A running Postgres instance (a local install, or `docker compose up postgres`)
- Docker, if you want to run the full `api` + `worker` + `postgres` stack via `docker-compose.yml` (see [Known limitations](#known-limitations) below)

## Setup and running

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` to point `DATABASE_URL` at your Postgres instance. Also change `STORAGE_DIR` to a directory you can actually write to when running outside Docker — the default `/data/storage` is meant for the Docker containers (see `docker-compose.yml`), and a local user typically won't have permission to create `/data` on their host. `STORAGE_DIR=./storage` works fine for local dev. See [Configuration](#configuration) below for every available setting.

### 3. Set up the database

```bash
alembic upgrade head
```

### 4. Run the API

```bash
uvicorn app.main:app --reload
```

The API is now at `http://localhost:8000` (interactive docs at `/docs`).

### 5. Run the worker

In a separate terminal (same `.env`, same virtualenv):

```bash
python -m app.worker
```

Without this running, uploaded images will stay at `status=pending` forever — the API never resizes images itself, only the worker does.

### Running via Docker Compose

```bash
docker compose up --build
```

This builds one image and runs it three ways: `api` (the FastAPI server, port `8000`), `worker` (`python -m app.worker`), and `postgres`. `api` and `worker` share a Docker volume for image storage, so the worker can read files the API saved and vice versa.

## Configuration

All settings are read from environment variables (or a `.env` file). See `.env.example` for a starting point.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | *(required)* | SQLAlchemy async Postgres URL, e.g. `postgresql+asyncpg://user:pass@host:5432/db` |
| `DATABASE_SSL` | `false` | Set `true` for SSL-required Postgres (e.g. DigitalOcean managed DB) |
| `DB_POOL_SIZE` | `5` | SQLAlchemy connection pool size |
| `DB_MAX_OVERFLOW` | `10` | Extra connections allowed beyond the pool size under load |
| `STORAGE_DIR` | `/data/storage` | Filesystem path where originals/thumbnails are stored. Use a locally-writable path (e.g. `./storage`) outside Docker |
| `MAX_FILE_SIZE_BYTES` | `10485760` (10MB) | Max size per uploaded file |
| `MAX_FILES_PER_REQUEST` | `20` | Max files accepted in a single `POST /images` |
| `MIN_CUSTOM_DIMENSION` / `MAX_CUSTOM_DIMENSION` | `1` / `4000` | Bounds for custom width/height requests |
| `WORKER_CONCURRENCY` | `1` | Number of jobs a single worker process resizes in parallel (via a thread pool) |
| `WORKER_POLL_INTERVAL_SECONDS` | `1.0` | How long a worker sleeps when there's no pending job |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL` |

Horizontal worker scaling (running multiple separate worker processes/containers, as opposed to `WORKER_CONCURRENCY`'s in-process thread pool) is done at the infrastructure level, e.g. `docker compose up --scale worker=3`.

## API reference

### `POST /images`

Multipart upload of one or more files, plus either a `preset` or `width`+`height` form field (applies to the whole batch).

```bash
curl -X POST http://localhost:8000/images \
  -F "files=@cat.jpg;type=image/jpeg" \
  -F "preset=medium"

# or with custom dimensions:
curl -X POST http://localhost:8000/images \
  -F "files=@cat.jpg;type=image/jpeg" \
  -F "width=300" -F "height=200"
```

Returns `202 Accepted` with an array of metadata objects (`status=pending`). Returns `400` if validation fails for any file in the batch — nothing is saved or inserted in that case.

### `GET /images/{id}`

```bash
curl http://localhost:8000/images/<id>
```

Returns current metadata (works at any status — `pending`, `processing`, `done`, or `failed`). `404` if the id doesn't exist.

### `GET /images/{id}/file`

```bash
curl -o thumbnail.jpg http://localhost:8000/images/<id>/file
```

Returns the thumbnail bytes once `status=done`. `404` if the id doesn't exist, or the image isn't done yet (poll `GET /images/{id}` and check `status` first).

### `GET /health`

Returns `200` with `{"status": "ok"}` if the API can reach Postgres, `503` otherwise.

### `GET /metrics`

Prometheus text-format metrics: image counts by status, total processed, average upload-to-completion time, and HTTP request counters labeled by method/route/status code.

## Running tests

Tests need a real Postgres instance (the test suite intentionally does not mock the database — the concurrency-safety guarantees this project is built around can only be verified against real Postgres row-locking behavior).

```bash
# create a test database once (adjust user/password to match your local Postgres):
PGPASSWORD=postgres psql -h localhost -U postgres -c "CREATE DATABASE thumbnails_test;"

pytest tests/ -v
```

- `tests/unit/` — pure functions (resize math, validation, content sniffing), no DB/filesystem.
- `tests/integration/` — repository queries, job claiming, worker processing, and each route, against real Postgres.
- `tests/e2e/` — concurrent uploads + concurrent worker processing, driven purely over HTTP.

Lint: `ruff check app tests`

CI (`.github/workflows/ci.yml`) runs both lint and the full test suite against a real `postgres:16` service container on every push to `main` and every PR.

## Known limitations

- `docker-compose.yml` (the `api` + `worker` + `postgres` multi-container setup) has not been run end to end in this development environment, since Docker was not available here. The individual pieces have been verified separately (the app boots via `uvicorn`, the worker runs via `python -m app.worker`, both against a real local Postgres instance), but the compose file's networking, build, and shared volume between `api` and `worker` have not been confirmed to work together. Please run `docker compose up --build` yourself to verify before relying on it.
- Deployment to DigitalOcean App Platform was attempted but is not currently working — the managed database connection string has repeatedly failed to parse correctly when set as an app-level environment variable. The Dockerfile, port configuration, and `GET /health` (DB connectivity check) have all been fixed and verified along the way; the remaining issue is specific to how the `DATABASE_URL` value is being entered in DigitalOcean's console.
- Image storage is local filesystem, not object storage — see [Extensions](#extensions) below.

## Extensions

- **Move file storage to DigitalOcean Spaces (S3-compatible object storage).** This is the biggest scalability limitation as built: local disk doesn't work once `api`/`worker` run as replicas across different physical hosts, only within one Docker host's shared volume. Only `app/services/storage.py` would need to change.
- **Split `images` into `originals` and `thumbnails` tables** if multiple thumbnail sizes per upload were ever needed (currently a strict 1:1 assumption, which matches the stated requirements but is a real constraint).
- **Swap Postgres-as-queue for Redis + RQ** once queue throughput or retry/backoff semantics become a real need — RQ supports multiple worker processes, automatic retries, and horizontal scaling out of the box. The migration is incremental: the job-claiming interface stays the same, only what's behind it changes.
- **Auth / client scoping.** No authentication currently exists; anyone who can reach the API can upload and read any image by id.
- **Optional `image_url` field** to let a client point at a remote image instead of uploading bytes directly (with the SSRF/timeout/size-limit precautions that implies).
- **Rate limiting** on `POST /images` — currently a single client could upload without any throttling.
- **Multiple `uvicorn` worker processes** (or a Gunicorn front-end) for the API itself — currently a single process handles all HTTP traffic.
- **A caching layer or CDN** in front of `GET /images/{id}/file` for frequently-requested thumbnails.
- **Request latency histograms** (p50/p95/p99 per route) — current metrics track counts, not duration.
