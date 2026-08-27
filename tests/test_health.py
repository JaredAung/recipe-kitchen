from fastapi.testclient import TestClient


def test_health_reports_ok(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["supabase"] is True


def test_me_requires_bearer_token(client: TestClient) -> None:
    response = client.get("/me")
    assert response.status_code == 401
