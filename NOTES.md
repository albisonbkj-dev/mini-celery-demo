# Mini Celery demo — notes from building it

Scratch doc: requirements, how I think the pieces fit, and what went wrong when I ran it. Not a second README; the real run instructions are in `README.md`.

---

## What the assignment wanted (in plain terms)

Someone types input in a page and hits submit. FastAPI hands work to Celery; the worker splits work into parallel-ish subtasks; results land in Redis; the browser polls by id and shows pending / running / done / failed. All of that should come up with `docker compose up` without installing Redis etc. on the host.

So it’s wiring: HTTP + broker + worker + UI + paths that match in Docker.

---

## Concepts I had to keep straight

- **FastAPI** — HTTP (`POST /jobs`, `GET /jobs/{id}` in our app; the brief mentioned other path names but same idea).
- **Broker** — where tasks are queued (Redis here).
- **Worker** — separate process that pulls from the broker and runs task code.
- **Result backend** — where Celery stores state/return value (same Redis host, different DB index in our config).
- **Compose** — runs api + worker + redis on one network; service names become hostnames (`redis`).

---

## Layout we ended up with

```
mini-celery-demo/
  app/
    main.py
    tasks.py
    celery_app.py
    schemas.py
    static/
      index.html
      app.js
  requirements.txt
  Dockerfile
  docker-compose.yml
  README.md
```

Dockerfile and compose live at **repo root** so `docker compose up` finds them. I had put compose under `app/` once and got “no configuration file” until I ran from the right place or passed `-f`.

---

## Endpoints this repo implements

- `POST /jobs` — body `{"numbers": [1,2,3]}` → returns `job_id`.
- `GET /jobs/{job_id}` — Celery status + `result` or `error` when terminal.

Optional extras from the brief (we didn’t need them for the demo): `/health`, separate result route.

---

## What “parallel tasks” means here

We use a **chord**: header = many `process_number` signatures, callback = `aggregate_results`. Celery runs the header tasks (concurrency permitting), then calls the callback with their return values as a list.

Important: the `job_id` we return is the async result for the **callback** (`aggregate_results`), not each `process_number`. So `PENDING` on that id can last the whole time the header tasks are still running — that confused me until I read it as “callback not finished yet,” not “nothing is happening.”

---

## Compose bits worth remembering

- **Redis** — broker DB `0`, results DB `1` in `celery_app.py`. We mapped host `6380 → 6379` because something else was already on `6379` on my machine.
- **api** — `uvicorn app.main:app`, port 8000, bind mount `.:/app`.
- **worker** — `celery -A app.celery_app:celery_app worker …`, same image/mount.

Inside containers the broker URL uses hostname **`redis`**, not `localhost`.

---

## Celery config (`app/celery_app.py`)

- `include=["app.tasks"]` — worker must **register** tasks. I hit `KeyError: 'app.tasks.run_parallel'` (or similar) when the worker didn’t load the module that defines the tasks. Adding `include` fixed it.
- `task_track_started=True` — you can see `STARTED` between `PENDING` and `SUCCESS` if you poll fast enough.
- `result_expires=3600` — results don’t sit in Redis forever.

---

## Tasks (`app/tasks.py`)

- `process_number(n)` — fake work (`sleep`), returns `{"input", "square"}`.
- `aggregate_results(results)` — Celery passes the list of dicts from the header. The `item` in `sum(item["square"] for item in results)` only exists inside that generator; don’t `print(item)` after the sum unless you define `item` in a loop.

I still have a `print(results)` in there sometimes when I’m watching the worker logs — delete for anything “clean.”

---

## API flow (`app/main.py`)

`POST /jobs` builds:

```python
chord(process_number.s(n) for n in payload.numbers)(aggregate_results.s())
```

Validates with `JobRequest`, returns `task.id` immediately (no blocking on work).

`GET /jobs/{id}` wraps `AsyncResult` — `SUCCESS` / `FAILURE` get special handling; everything else (e.g. `PENDING`, `STARTED`) passes through as `status`.

---

## Why I stopped using `group(...).get()` inside one big task

Celery complained: **never call `result.get()` inside a task** (sync wait on subtasks from inside a task). So the orchestration moved to a **chord** started from the API instead of one parent task that `.get()`’s the group.

---

## Frontend

Vanilla JS: parse commas → `POST /jobs` → poll `GET /jobs/{id}` every ~1.5s until `SUCCESS` or `FAILURE`, then dump JSON into the page.

---

## Quick “did I break it?” checklist

- Compose comes up; worker connects to Redis (no broker URL typos vs api).
- Submit job; `job_id` appears; status eventually hits `SUCCESS` with `items` and `sum_of_squares`.
- If status sticks on `PENDING` forever — worker logs usually tell you (unregistered task, exception, wrong app id).

---

## Who sets `PENDING`?

Not FastAPI magic — **`AsyncResult(...).status`** comes from Celery’s result backend. Until the task behind that id is finished, you’re in a non-terminal state; **`PENDING`** is the usual label for “not done yet.” For our chord, that id is the callback’s result, so pending includes “header still running.”

---

### Filename

I renamed this file from `PROJECT_PLAN_AND_DEBUGGING.md` to **`NOTES.md`** so it reads like personal build notes. If you prefer something more explicit, **`BUILD_NOTES.md`** works too.
