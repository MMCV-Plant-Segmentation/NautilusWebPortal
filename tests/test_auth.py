from nautilus_web_portal.db import get_db


def test_login_success(client):
    r = client.post("/api/login", json={"username": "admin", "password": "adminpass123"})
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}


def test_login_wrong_password(client):
    r = client.post("/api/login", json={"username": "admin", "password": "wrongpass"})
    assert r.status_code == 401


def test_login_nonexistent_user(client):
    r = client.post("/api/login", json={"username": "nobody", "password": "pass"})
    assert r.status_code == 401


def test_login_no_password_set(admin_client, client):
    # A freshly created user has no password_hash set yet — use the API to create one
    admin_client.post("/api/users", json={"username": "nopass"})
    r = client.post("/api/login", json={"username": "nopass", "password": "anything"})
    assert r.status_code == 401


def test_logout_authenticated(admin_client):
    r = admin_client.post("/api/logout")
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}


def test_logout_unauthenticated(client):
    r = client.post("/api/logout")
    assert r.status_code == 401


def test_me_authenticated(admin_client):
    r = admin_client.get("/api/me")
    assert r.status_code == 200
    data = r.get_json()
    assert data["username"] == "admin"
    assert data["is_admin"] is True


def test_me_unauthenticated(client):
    r = client.get("/api/me")
    assert r.status_code == 401


def test_stale_token_rejected(app, client):
    """Cookie present but token deleted from DB is rejected (not the same as never logged in)."""
    client.post("/api/login", json={"username": "admin", "password": "adminpass123"})
    with app.app_context():
        db = get_db()
        db.execute("DELETE FROM auth_tokens")
        db.commit()
    r = client.get("/api/users")
    assert r.status_code == 401
