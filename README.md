# Otis

AI Farm model requests, end to end: a questionnaire, a queue and an emailed
result. Built with **FastAPI** + **Celery**.

The HTTP API is versioned under **`/v1`**; only the UI lives at the root.

| method | path | what it does |
|--------|------|--------------|
| `GET` | `/` | the questionnaire (the only unversioned route) |
| `POST` | `/v1/data` | store a `.zip` dataset, return its link |
| `POST` | `/v1/model` | request a model for an uploaded dataset |
| `GET` | `/v1/health` | liveness probe |

## Flow

1. The user fills in the questionnaire at `/`: **email**, **model type**,
   **model size** and a **`.zip` dataset**. On submit the page calls
   `POST /v1/data` with the file, gets a link back, and passes that link to
   `POST /v1/model` together with the other three answers.
2. The request (`email`, `upload_link`, `model_size`, `product_id`) is validated
   and **stored in PostgreSQL**, then a **Celery job** is enqueued with the new
   submission id.
3. The Celery worker (`aifarm.job.process_submission`) runs the job:
   - the **AI Farm runner** **fetches** the `upload_link` — from object storage
     when the link is one of ours, over HTTP otherwise — and **unzips** it (must
     be a zip, otherwise it raises) into a temporary directory that is removed
     as soon as the data has been consumed,
   - the dataset is handed to the **AI Farm service** (see below),
   - the result zip is **uploaded to object storage** and the submitter is
     **emailed a pre-signed download link** (results are too big to attach).
4. On **any error** the submission is marked `FAILED`, the reason is logged, and
   an error email is sent to the submitter. Every step is logged.

## Products

`product_id` is the AI Farm product the user ordered. `POST /v1/model` accepts
it as the bare id (`1`, `"1"`) or as its name, with or without a leading number
(`"1. Image Classification"`, `"Image Classification"`).

| id | product | id | product |
|----|---------|----|---------|
| 1 | Image Classification | 7 | Tabular Features Regression |
| 2 | Time Series Classification | 8 | Multi Modal Regression |
| 3 | Tabular Features Classification | 9 | Multi Modal Multi Head Classification and Regression |
| 4 | Multi Modal Classification | 10 | Image Segmentation |
| 5 | Image Regression | 11 | Image Detection |
| 6 | Time Series Regression | | |

## AI Farm

`AIFarmService` (`src/aifarm/service.py`) runs the AI Farm script. That script
polls fixed directories under `AIFARM_ROOT`, so a run means:

1. `from_user` and `to_user` are cleared,
2. the extracted upload is copied to `from_user/data`, then `info.csv` is
   written **last** (a data directory without it is treated as a failed upload
   by the script). Its contents come from `AIFARM_INFO_CSV_TEMPLATE`:

   ```
   Product id (Image Classification):,1
   What size do you demand for the model?,"""tiny"""
   ```

3. `python3 <AIFARM_ROOT>/<AIFARM_SCRIPT_NAME>` is started; the script reads the
   product id and runs `<id>.py`,
4. Otis polls until `to_user` exists and the script has removed `from_user/data`
   (or gives up after `TIMEOUT_SECONDS`), then stops the script — it loops
   forever and never exits on its own,
5. a `to_user/Error_Status.csv` is raised as a failure; otherwise `to_user` is
   zipped and emailed,
6. `from_user` and `to_user` are removed again, whatever the outcome.

**One run at a time.** Those directories are global, so a job takes a Redis lock
before running; a job that finds it taken re-queues itself 30s later instead of
blocking the worker. Workers also run with `--concurrency=1`.

The worker must therefore run on the machine that holds `AIFARM_ROOT` (in Docker,
bind-mount it into the `worker` service — see `docker-compose.yml`).

## Questionnaire

`GET /` serves the form (`src/ui/`, static assets under `src/ui/static/`)
carrying the AI Farm logo. It collects the four answers and submits in two
steps — dataset first, then the request that references it — showing upload
progress in between. The page only ever talks to the two `/v1` endpoints; no
storage credentials reach the browser.

`POST /v1/data` (`src/data/`) validates the archive by extension **and** magic
bytes, streams it to `uploads/<uuid>/<filename>.zip` without buffering it on the
API's disk, and returns `{filename, key, link}`. Uploads above
`MAX_UPLOAD_BYTES` (2 GB, `src/data/router.py`) are refused on `Content-Length`.

`POST /v1/model` (`src/model/`) stores the request and queues the job.

Both are **unauthenticated**: the questionnaire is public and a browser cannot
hold a secret. Put a rate limit, a captcha or a reverse proxy in front before
exposing them — `/v1/model` queues GPU work.

The worker later resolves that link back to its object key and downloads it
**with credentials**, so a signature that expired while the questionnaire sat
half-finished does not break the job. Links that are not ours still go over
plain HTTP.

## Result delivery

Result archives are not attached to the email. `MinioClient`
(`src/infrastructure/minio/client.py`) uploads them to any S3-compatible store —
Cloudflare R2 in production, MinIO locally — under
`results/<submission id>/<timestamp>-aifarm_result.zip`, and returns a
**pre-signed** GET link so the bucket can stay private. The link goes into
`GMAIL_RESULT_BODY` via its `{download_link}` and `{expires_in}` placeholders
and expires after `MINIO_LINK_EXPIRY_SECONDS` (7 days is the signature maximum).

## Project layout

```
src/
  otis/            # app core: config, logging, FastAPI factory, exceptions,
                   # models.py (ORM), repository.py (data access)
  model/           # POST /v1/model: router, schemas, service (store + enqueue)
  data/            # POST /v1/data: router, schemas, service (validate + store)
  ui/              # GET /: router + static/ (questionnaire, logo, css, js)
  aifarm/          # service.py (runs the AI Farm script), products.py
                   # (catalogue), runner.py (orchestration), job.py (Celery task)
  util/            # http.py (download), file.py (unzip)
  infrastructure/
    db/            # base, session
    celery/        # celery app
    redis/         # lock.py - one AI Farm run at a time
    minio/         # client.py - S3-compatible result storage + signed links
    mail/          # Gmail SMTP sender
migrations/        # Alembic environment + versions
entrypoints/           # run.sh, worker.sh, migrate.sh, makemigration.sh
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
(`entrypoints/run.sh` applies migrations then serves on http://localhost:8000) and
the Celery `worker`.

## Run locally

```bash
uv sync
./entrypoints/migrate.sh                 # apply migrations
./entrypoints/run.sh                     # API (migrate + uvicorn)
./entrypoints/worker.sh                  # Celery worker (separate shell)
./entrypoints/makemigration.sh "msg"     # create a new migration
```

## Example request

The same two steps the questionnaire performs:

```bash
# 1. store the dataset, keep the link it returns
LINK=$(curl -s -F "file=@dataset.zip" http://localhost:8000/v1/data | jq -r .link)

# 2. request the model for it
curl -X POST http://localhost:8000/v1/model \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"test@test.com\",
    \"upload_link\": \"$LINK\",
    \"model_size\": \"Medium\",
    \"product_id\": \"1. Image Classification\"
  }"
```
