import os
from collections.abc import Generator
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/test")
os.environ.setdefault("AWS_REGION", "us-east-1")

from recipe_kitchen.api.deps import get_current_user  # noqa: E402
from recipe_kitchen.main import app  # noqa: E402

TEST_USER_ID = UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_client() -> Generator[TestClient]:
    app.dependency_overrides[get_current_user] = lambda: {"sub": str(TEST_USER_ID)}
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
