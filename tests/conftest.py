import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_PUBLISHABLE_KEY", "test-publishable-key")
os.environ.setdefault("SUPABASE_SECRET_KEY", "test-secret-key")
os.environ.setdefault("SQS_QUEUE_URL", "https://sqs.us-east-1.amazonaws.com/123/test")
os.environ.setdefault("AWS_REGION", "us-east-1")

from recipe_kitchen.main import app  # noqa: E402


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
