import pytest

from nautilus_web_portal import create_app
from nautilus_web_portal.db import init_db


def test_init_db_updates_existing_admin_password(app, client):
    """Re-running init_db with a new ADMIN_PASSWORD updates the stored hash."""
    app.config["ADMIN_PASSWORD"] = "newpassword123"
    with app.app_context():
        init_db()
    r = client.post("/api/login", json={"username": "admin", "password": "newpassword123"})
    assert r.status_code == 200


def test_init_db_no_admin_no_password_raises(tmp_path):
    """First run with no existing admin and no ADMIN_PASSWORD raises RuntimeError."""
    application = create_app({
        "TESTING": True,
        "SECRET_KEY": "test",
        "DATABASE": str(tmp_path / "fresh.db"),
        "HASH_METHOD": "pbkdf2:sha256:1",
    })
    with pytest.raises(RuntimeError, match="ADMIN_PASSWORD"):
        with application.app_context():
            init_db()
