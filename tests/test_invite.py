import time
from unittest.mock import patch

EIGHT_DAYS = 8 * 24 * 3600  # past the 7-day TTL


# ── helpers ───────────────────────────────────────────────────────────────────

def _create_alice_with_token(admin_client):
    r = admin_client.post("/api/users", json={"username": "alice"})
    assert r.status_code == 201
    data = r.get_json()
    return data["id"], data["invite"]["token"]


def _in_the_future(offset=EIGHT_DAYS):
    """Return a context manager that freezes time.time() in api.py to now + offset."""
    return patch("nautilus_web_portal.invites.time.time", return_value=time.time() + offset)


# ── GET /api/invite/<token> ───────────────────────────────────────────────────

def test_get_invite_valid(admin_client):
    _, token = _create_alice_with_token(admin_client)
    r = admin_client.get(f"/api/invite/{token}")
    assert r.status_code == 200
    assert r.get_json()["username"] == "alice"


def test_get_invite_expired(admin_client):
    _, token = _create_alice_with_token(admin_client)
    with _in_the_future():
        r = admin_client.get(f"/api/invite/{token}")
    assert r.status_code == 403


def test_get_invite_invalid_token(client):
    r = client.get("/api/invite/totallybogustoken")
    assert r.status_code == 403


# ── POST /api/invite/<token> ──────────────────────────────────────────────────

def test_redeem_invite_success(client, admin_client):
    _, token = _create_alice_with_token(admin_client)
    r = client.post(f"/api/invite/{token}", json={"password": "newpass1", "confirm": "newpass1"})
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}


def test_get_invite_clears_auth(admin_client):
    """Loading a valid invite link clears the caller's auth token."""
    _, token = _create_alice_with_token(admin_client)
    admin_client.get(f"/api/invite/{token}")
    r = admin_client.get("/api/users")
    assert r.status_code == 401


def test_redeem_invite_clears_auth(app, admin_client):
    """Redeeming an invite clears the caller's auth token."""
    _, token = _create_alice_with_token(admin_client)
    admin_client.post(f"/api/invite/{token}", json={"password": "newpass1", "confirm": "newpass1"})
    r = admin_client.get("/api/users")
    assert r.status_code == 401


def test_redeem_invite_password_mismatch(client, admin_client):
    _, token = _create_alice_with_token(admin_client)
    r = client.post(f"/api/invite/{token}", json={"password": "newpass1", "confirm": "different"})
    assert r.status_code == 400


def test_redeem_invite_too_short(client, admin_client):
    _, token = _create_alice_with_token(admin_client)
    r = client.post(f"/api/invite/{token}", json={"password": "short", "confirm": "short"})
    assert r.status_code == 400


def test_redeem_invite_expired(client, admin_client):
    _, token = _create_alice_with_token(admin_client)
    with _in_the_future():
        r = client.post(f"/api/invite/{token}", json={"password": "newpass1", "confirm": "newpass1"})
    assert r.status_code == 403


def test_redeem_invite_consumes_token(client, admin_client):
    _, token = _create_alice_with_token(admin_client)
    client.post(f"/api/invite/{token}", json={"password": "newpass1", "confirm": "newpass1"})
    r = client.post(f"/api/invite/{token}", json={"password": "newpass1", "confirm": "newpass1"})
    assert r.status_code == 403


def test_full_invite_flow(client, admin_client):
    """Create user → redeem invite → log in with new password."""
    _, token = _create_alice_with_token(admin_client)
    client.post(f"/api/invite/{token}", json={"password": "alicepass", "confirm": "alicepass"})
    r = client.post("/api/login", json={"username": "alice", "password": "alicepass"})
    assert r.status_code == 200
    assert r.get_json() == {"ok": True}
