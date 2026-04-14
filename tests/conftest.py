import pytest

from nautilus_web_portal import create_app
from nautilus_web_portal.db import init_db


@pytest.fixture
def app(tmp_path):
    db_path = str(tmp_path / "test.db")
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": db_path,
        "ADMIN_PASSWORD": "adminpass123",
    })
    with application.app_context():
        init_db()
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """A test client already authenticated as admin."""
    client.post("/api/login", json={"username": "admin", "password": "adminpass123"})
    return client
