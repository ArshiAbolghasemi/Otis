# Otis

Webhook-driven AI Farm processing service built with **FastAPI** + **Celery**.

## Flow

1. A Porsline webhook `POST /webhook` arrives with an `x-api-key` header.
2. The payload (`email`, `upload_link`, `model_size`, `model_type`) is validated
   and **stored in PostgreSQL**, then a **Celery job** is enqueued with the new
   submission id.
3. The Celery worker (`aifarm.job.process_submission`) runs the job:
   - the **AI Farm runner** **downloads** the `upload_link` (must be a zip,
     otherwise it raises) and **unzips** it into a temporary directory that is
     removed as soon as the data files have been consumed,
   - the data files are passed to the **AI Farm service** (placeholder —
     returns a sample result zip),
   - **emails** the result zip to the submitter.
4. On **any error** the submission is marked `FAILED`, the reason is logged, and
   an error email is sent to the submitter. Every step is logged.

## Project layout

```
src/
  otis/            # app core: config, logging, FastAPI factory, exceptions,
                   # models.py (ORM), repository.py (data access)
  webhook/         # router, schemas (API models), service (store + enqueue), deps
  aifarm/          # runner (orchestration), service (sample-zip placeholder),
                   # job.py (Celery task)
  util/            # http.py (download), file.py (unzip)
  infrastructure/
    db/            # base, session
    celery/        # celery app
    mail/          # Gmail SMTP sender
migrations/        # Alembic environment + versions
scripts/           # run.sh, worker.sh, migrate.sh, makemigration.sh
alembic.ini
```

## Configuration

Copy `.env.example` to `.env` and fill in the values (`.env` holds real secrets
and is git-ignored). Gmail needs an **app password**; without valid SMTP
credentials the pipeline still runs but the final mail step fails (and is
reported as `FAILED`).

## Run with Docker

```bash
docker compose up --build
```

Starts PostgreSQL (official `postgres:16-alpine` image), Redis, the API
(`scripts/run.sh` applies migrations then serves on http://localhost:8000) and
the Celery `worker`.

## Run locally

```bash
uv sync
./scripts/migrate.sh                 # apply migrations
./scripts/run.sh                     # API (migrate + uvicorn)
./scripts/worker.sh                  # Celery worker (separate shell)
./scripts/makemigration.sh "msg"     # create a new migration
```

## Example request

```bash
curl -X POST http://localhost:8000/webhook \
  -H "x-api-key: 3ykYIdJNM3ORGLgxBUjE0A6rqr0WG61V" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@test.com",
    "upload_link": "https://example.com/dataset.zip",
    "model_size": "Medium",
    "model_type": "Linear Regression"
  }'
```
