from pydantic import BaseModel, Field


class JobRequest(BaseModel):
    numbers: list[int] = Field(..., min_length=1, max_length=50)


class JobCreated(BaseModel):
    job_id: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error: str | None = None