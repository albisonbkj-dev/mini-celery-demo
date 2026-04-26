from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_job_rejects_empty_numbers():
    r = client.post("/jobs", json={"numbers": []})
    assert r.status_code == 422


def test_create_job_rejects_too_many_numbers():
    r = client.post("/jobs", json={"numbers": list(range(51))})
    assert r.status_code == 422
