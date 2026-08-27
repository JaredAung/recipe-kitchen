from fastapi.testclient import TestClient


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
