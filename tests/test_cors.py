from fastapi.testclient import TestClient

FRONTEND_ORIGIN = "http://localhost:3000"


def test_cors_allows_frontend_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": FRONTEND_ORIGIN})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == FRONTEND_ORIGIN


def test_cors_preflight_allows_frontend_origin(client: TestClient) -> None:
    response = client.options(
        "/ingest",
        headers={
            "Origin": FRONTEND_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == FRONTEND_ORIGIN


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
