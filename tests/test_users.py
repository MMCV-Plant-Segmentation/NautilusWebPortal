# ── helpers ──────────────────────────────────────────────────────────────────

def _create_alice(admin_client):
    """Create a user named 'alice' and return the parsed JSON response."""
    r = admin_client.post("/api/users", json={"username": "alice"})
    assert r.status_code == 201
    return r.get_json()


def _make_non_admin_client(client, admin_client):
    """Create alice, set her password via invite, return a client logged in as her."""
    user = _create_alice(admin_client)
    token = user["invite"]["token"]
    client.post(f"/api/invite/{token}", json={"password": "alicepass", "confirm": "alicepass"})
    client.post("/api/login", json={"username": "alice", "password": "alicepass"})
    return client


def _admin_id(admin_client):
    users = admin_client.get("/api/users").get_json()
    return next(u["id"] for u in users if u["username"] == "admin")


# ── list users ────────────────────────────────────────────────────────────────

def test_list_users_as_admin(admin_client):
    r = admin_client.get("/api/users")
    assert r.status_code == 200
    users = r.get_json()
    assert any(u["username"] == "admin" for u in users)


def test_list_users_unauthenticated(client):
    r = client.get("/api/users")
    assert r.status_code == 401


def test_list_users_as_non_admin(client, admin_client):
    non_admin = _make_non_admin_client(client, admin_client)
    r = non_admin.get("/api/users")
    assert r.status_code == 403


# ── create user ───────────────────────────────────────────────────────────────

def test_create_user(admin_client):
    r = admin_client.post("/api/users", json={"username": "alice"})
    assert r.status_code == 201
    data = r.get_json()
    assert data["username"] == "alice"
    assert data["has_password"] is False
    assert data["invite"] is not None
    assert "token" in data["invite"]


def test_create_user_duplicate(admin_client):
    admin_client.post("/api/users", json={"username": "alice"})
    r = admin_client.post("/api/users", json={"username": "alice"})
    assert r.status_code == 409


def test_create_user_empty_username(admin_client):
    r = admin_client.post("/api/users", json={"username": ""})
    assert r.status_code == 400


# ── reset user ────────────────────────────────────────────────────────────────

def test_reset_user(admin_client):
    user = _create_alice(admin_client)
    r = admin_client.post(f"/api/users/{user['id']}/reset")
    assert r.status_code == 200
    data = r.get_json()
    assert data["has_password"] is False
    assert data["invite"] is not None


def test_reset_admin_forbidden(admin_client):
    r = admin_client.post(f"/api/users/{_admin_id(admin_client)}/reset")
    assert r.status_code == 403


def test_reset_nonexistent_user(admin_client):
    r = admin_client.post("/api/users/9999/reset")
    assert r.status_code == 404


# ── delete user ───────────────────────────────────────────────────────────────

def test_delete_user(admin_client):
    user = _create_alice(admin_client)
    r = admin_client.delete(f"/api/users/{user['id']}")
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}


def test_delete_admin_forbidden(admin_client):
    r = admin_client.delete(f"/api/users/{_admin_id(admin_client)}")
    assert r.status_code == 403


def test_delete_nonexistent_user(admin_client):
    r = admin_client.delete("/api/users/9999")
    assert r.status_code == 404
