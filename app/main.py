from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from celery import chord
from celery.result import AsyncResult

from app.schemas import JobRequest, JobCreated, JobStatus
from app.tasks import process_number, aggregate_results
from app.celery_app import celery_app

app = FastAPI(title="Mini Celery Demo")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
def health():
    """Lightweight check for load balancers and compose; does not verify Redis."""
    return {"status": "ok"}


@app.get("/")
def root():
    return FileResponse("app/static/index.html")


@app.post("/jobs", response_model=JobCreated)
def create_job(payload: JobRequest):
    task = chord(process_number.s(n) for n in payload.numbers)(aggregate_results.s())
    return JobCreated(job_id=task.id)


@app.get("/jobs/{job_id}", response_model=JobStatus)
def get_job(job_id: str):
    task = AsyncResult(job_id, app=celery_app)
    status = task.status

    if status == "SUCCESS":
        return JobStatus(job_id=job_id, status=status, result=task.result)
    if status == "FAILURE":
        return JobStatus(job_id=job_id, status=status, error=str(task.result))

    return JobStatus(job_id=job_id, status=status)