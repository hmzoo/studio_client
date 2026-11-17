"""Configuration des tests : base SQLite, passerelle fake, stockage temporaire."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="studio_client_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_tmp, 'test.db')}"
os.environ["GENERATION_GATEWAY_MODE"] = "fake"
os.environ["GENERATION_API_BASE_URL"] = "https://api.example.com"
os.environ["STUDIO_STORAGE_DIR"] = os.path.join(_tmp, "media")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from studio.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c
