import os

# Must be set before the app is imported: tests never touch a real database or .env secrets.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["DEV_AUTH"] = "1"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings, get_settings  # noqa: E402
from app.db.base import Base, create_all, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def _fresh_db():
    create_all()
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def client():
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


@pytest.fixture
def no_dev_auth():
    """Run the request as a deployment without DEV_AUTH."""
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, dev_auth=False)
    yield
    app.dependency_overrides.clear()


def assert_error_shape(body: dict) -> None:
    assert set(body) == {"code", "message", "details"}
    assert isinstance(body["code"], str) and isinstance(body["message"], str)
    assert body["details"] is None or isinstance(body["details"], dict)
