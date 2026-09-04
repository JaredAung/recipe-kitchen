from unittest.mock import patch

from fastapi.testclient import TestClient

ENQUEUE = "recipe_kitchen.api.routes.ingest.enqueue_job"


def test_ingest_rejects_non_facebook_url(client: TestClient) -> None:
    response = client.post("/ingest", json={"url": "https://example.com/video"})
    assert response.status_code == 422


def test_ingest_rejects_facebook_profile_url(client: TestClient) -> None:
    response = client.post("/ingest", json={"url": "https://www.facebook.com/someone"})
    assert response.status_code == 422


def test_ingest_enqueues_facebook_url(client: TestClient) -> None:
    with patch(ENQUEUE, return_value="job-ingest") as enqueue:
        response = client.post(
            "/ingest",
            json={"url": "https://www.facebook.com/reel/123"},
        )

    assert response.status_code == 202
    assert response.json() == {"job_id": "job-ingest"}
    kind, payload = enqueue.call_args.args
    assert kind == "ingest"
    assert "facebook.com/reel/123" in payload["url"]


def test_ingest_returns_502_when_enqueue_fails(client: TestClient) -> None:
    with patch(ENQUEUE, side_effect=RuntimeError("Failed to enqueue job")):
        response = client.post(
            "/ingest",
            json={"url": "https://www.facebook.com/reel/123"},
        )
    assert response.status_code == 502
