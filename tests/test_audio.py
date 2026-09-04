from unittest.mock import patch

from fastapi.testclient import TestClient

ENQUEUE = "recipe_kitchen.api.routes.audio.enqueue_upload_job"


def test_audio_rejects_unsupported_type(client: TestClient) -> None:
    response = client.post(
        "/audio",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_audio_rejects_empty_file(client: TestClient) -> None:
    response = client.post(
        "/audio",
        files={"file": ("video.mp4", b"", "video/mp4")},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Uploaded file is empty."


def test_audio_rejects_oversize_file(client: TestClient) -> None:
    with patch("recipe_kitchen.api.uploads.MAX_UPLOAD_BYTES", 4):
        response = client.post(
            "/audio",
            files={"file": ("video.mp4", b"12345", "video/mp4")},
        )
    assert response.status_code == 413
    assert response.json()["detail"] == "File too large."


def test_audio_enqueues_upload(client: TestClient) -> None:
    with patch(ENQUEUE, return_value="job-audio") as enqueue:
        response = client.post(
            "/audio",
            files={"file": ("clip.mp4", b"fake", "video/mp4")},
        )

    assert response.status_code == 202
    assert response.json() == {"job_id": "job-audio"}
    kind, tmp_path = enqueue.call_args.args
    assert kind == "audio"
    assert enqueue.call_args.kwargs["suffix"] == ".mp4"
    assert enqueue.call_args.kwargs["original_filename"] == "clip.mp4"
    assert not tmp_path.exists()
