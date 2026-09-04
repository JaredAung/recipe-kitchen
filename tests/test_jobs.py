from unittest.mock import patch

from fastapi.testclient import TestClient

from recipe_kitchen.schemas.jobs import Job

FETCH = "recipe_kitchen.api.routes.jobs.fetch_job"


def test_get_job_not_found(client: TestClient) -> None:
    with patch(FETCH, return_value=None):
        response = client.get("/jobs/missing")
    assert response.status_code == 404


def test_get_job_running(client: TestClient) -> None:
    job = Job(id="job-1", kind="recipe", status="running", input={"caption": "x"})
    with patch(FETCH, return_value=job):
        response = client.get("/jobs/job-1")
    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == "job-1"
    assert body["kind"] == "recipe"
    assert body["status"] == "running"
    assert body["result"] is None
    assert body["error"] == ""


def test_get_job_succeeded(client: TestClient) -> None:
    job = Job(
        id="job-1",
        kind="recipe",
        status="succeeded",
        result={"id": "abc", "stopped_after": "caption", "sufficient": True},
    )
    with patch(FETCH, return_value=job):
        response = client.get("/jobs/job-1")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["result"]["id"] == "abc"
