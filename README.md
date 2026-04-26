## Mini Celery Demo

FastAPI + Celery + Redis demo for running parallel background tasks.

### Services

- `api`: FastAPI app (`http://localhost:8000`)
- `worker`: Celery worker
- `redis`: broker/result backend

### Run

```bash
docker compose up --build
```

### Flow

1. `POST /jobs` submits numbers.
2. API creates a Celery `chord`:
   - parallel `process_number` tasks
   - callback `aggregate_results`
3. `GET /jobs/{id}` returns Celery status/result.

### Notes

- Celery task registration is configured via `include=["app.tasks"]` in `app/celery_app.py`.
- The implementation avoids calling `.get()` inside a task to prevent Celery runtime failures.

### Tracing chord states (step-by-step sample)

In this app, `POST /jobs` returns `job_id` from:

```python
chord(process_number.s(n) for n in payload.numbers)(aggregate_results.s())
```

That id is the **async result for the chord’s callback** — here, `aggregate_results`. The API only exposes this one id; each `process_number` run also gets its own task id internally (visible in worker logs).

**Example:** `POST /jobs` with body `{"numbers":[1,2,3,4]}`.

| Step | What Celery is doing | `GET /jobs/{job_id}` → `status` | `result` / `error` |
|------|----------------------|----------------------------------|----------------------|
| 1 | Request returns immediately. Callback task is registered; header group (`process_number` × 4) is queued. | `PENDING` | `result: null` |
| 2 | Worker(s) execute `process_number` (possibly in parallel). Callback **cannot** finish until all four return. | Still `PENDING` (callback not done yet) | `null` |
| 3 | All four `process_number` tasks succeeded. Celery enqueues `aggregate_results` with `results=[{...},{...},{...},{...}]`. | Often still `PENDING` until the worker picks up the callback | `null` |
| 4 | Worker runs `aggregate_results` (with `task_track_started=True`, may briefly show `STARTED`). | `STARTED` (optional; can be fast) | `null` |
| 5 | Callback returns `{"items": [...], "sum_of_squares": 30}`. | `SUCCESS` | Full dict in `result` |
| (failure) | Any header task raises, or callback raises. | `FAILURE` | `error` set; exception info in `task.result` |

**How to correlate with the worker**

- Watch the worker container logs: you should see `process_number` invocations first, then `aggregate_results`.
- Each log line for a task includes that task’s **own** id (not always the same as `job_id`).

**Inspect a stored result from the shell** (replace `JOB_ID` and ensure stack is up):

```bash
docker compose exec worker celery -A app.celery_app:celery_app result JOB_ID
```

That prints the final result if status is `SUCCESS`, or helps confirm failure state.

**Why `PENDING` can last several seconds**

Each `process_number` sleeps 2 seconds. With enough concurrency, four can finish in ~2s; with `--concurrency=1`, they run one after another (~8s) before `aggregate_results` runs — `job_id` stays `PENDING` for that whole time because you are polling the **callback** result, not the individual header tasks.
