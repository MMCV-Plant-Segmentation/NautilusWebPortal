# Restructure & Test Plan

## Overview

Two goals:
1. Move the flat source files into a proper `nautilus_web_portal` Python package.
2. Add a comprehensive pytest test suite covering all API endpoints.

No behaviour changes — only refactoring and new tests.

---

## New File Structure

```
NautilusWebPortal/
├── nautilus_web_portal/          NEW directory (Python package)
│   ├── __init__.py               NEW — contains create_app()
│   ├── api.py                    MOVED from root, imports updated
│   ├── views.py                  MOVED from root, imports updated
│   ├── db.py                     MOVED from root, significant changes (see below)
│   └── templates/                MOVED from root/templates/
│       ├── base.html
│       ├── index.html
│       ├── login.html
│       ├── admin.html
│       ├── invite.html
│       └── invite_invalid.html
├── tests/                        NEW directory
│   ├── conftest.py               NEW — shared pytest fixtures
│   ├── test_auth.py              NEW — login / logout
│   ├── test_users.py             NEW — user CRUD
│   └── test_invite.py            NEW — invite flow
├── app.py                        MODIFIED — thin entry point only
├── pyproject.toml                MODIFIED — add dev group + pytest config
├── Dockerfile                    MODIFIED — updated COPY commands
├── kubewrapper.py                UNCHANGED
├── compose.yaml                  UNCHANGED
├── uv.lock                       REGENERATED after pyproject change
├── README.md                     UNCHANGED (for now)
└── .gitignore                    UNCHANGED
```

Root-level `api.py`, `views.py`, `db.py`, and `templates/` are **deleted** once the package
directory contains their replacements.

---

## `pyproject.toml`

Add a dev dependency group and pytest config:

```toml
[project]
name = "nautilus-web-portal"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "flask",
]

[dependency-groups]
dev = ["pytest>=8"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

After editing, run `uv add --group dev pytest` (or just `uv sync --group dev`) to
regenerate `uv.lock`. Commit the updated lock file.

---

## `nautilus_web_portal/__init__.py`

Contains `create_app(test_config=None)`. Accepts an optional dict for tests; reads
environment variables when `test_config` is `None`.

```python
import os
from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__)

    if test_config is None:
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
        app.config["DATABASE"] = os.path.expanduser("~/nwp/db.sqlite3")
        app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD")
    else:
        app.config.update(test_config)

    from .db import close_db
    from .api import api_bp
    from .views import views_bp

    app.teardown_appcontext(close_db)
    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)
    return app
```

Flask resolves templates relative to the package root (`nautilus_web_portal/`), so
`nautilus_web_portal/templates/` is found automatically by `Flask(__name__)`.

---

## `nautilus_web_portal/db.py`

### Key change: remove the module-level `DB_PATH` constant

`get_db()` and `init_db()` now read the path from `current_app.config["DATABASE"]`,
and `init_db()` reads `ADMIN_PASSWORD` from `current_app.config["ADMIN_PASSWORD"]`
instead of `os.environ`.

```python
import os
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db_path = current_app.config["DATABASE"]
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    db = sqlite3.connect(db_path)
    db.execute("PRAGMA foreign_keys = ON")
    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT,
            created_at    REAL    NOT NULL DEFAULT (unixepoch())
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS invite_codes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token      TEXT    UNIQUE NOT NULL,
            expires    REAL    NOT NULL,
            created_at REAL    NOT NULL DEFAULT (unixepoch())
        )
    """)
    db.commit()

    admin_password = current_app.config.get("ADMIN_PASSWORD")
    admin = db.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()

    if admin and admin_password:
        db.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (generate_password_hash(admin_password),),
        )
        db.commit()
    elif not admin and admin_password:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES ('admin', ?)",
            (generate_password_hash(admin_password),),
        )
        db.commit()
    elif not admin:
        raise RuntimeError(
            "ADMIN_PASSWORD environment variable is required on first run "
            "(no admin account exists yet)."
        )
    # admin exists, ADMIN_PASSWORD absent → leave password unchanged

    db.close()
```

---

## `nautilus_web_portal/api.py`

Identical logic to current `api.py`. Only change: update the import at the top from
`from db import get_db` to `from .db import get_db` (relative import).

---

## `nautilus_web_portal/views.py`

Identical logic to current `views.py`. No imports from `db` needed; no import change
required beyond moving the file.

---

## `app.py` (root-level entry point)

Trimmed to a thin entry point. `create_app()` and `init_db()` come from the package.
`init_db()` requires an app context, so it's wrapped in `with app.app_context()`.

```python
import os

from nautilus_web_portal import create_app
from nautilus_web_portal.db import init_db

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=int(os.environ["PORT"]), debug=False)
```

---

## `Dockerfile` Changes

Replace the `COPY` commands for application code:

```dockerfile
# Old:
COPY kubewrapper.py app.py api.py views.py db.py ./
COPY templates/ ./templates/

# New:
COPY nautilus_web_portal/ ./nautilus_web_portal/
COPY app.py kubewrapper.py ./
```

Templates are now inside the package directory, so no separate `COPY templates/` step.
Everything else in the Dockerfile is unchanged.

---

## Tests

### Why `tmp_path` instead of `:memory:`

SQLite `:memory:` databases are connection-scoped — each `sqlite3.connect(":memory:")`
opens a completely separate, empty database. Because `init_db()` opens its own
connection (outside Flask's `g`) and `get_db()` opens a second one per request, they
would see different databases. Using a real temp file (via pytest's built-in `tmp_path`
fixture) avoids this entirely — both connections reach the same file. pytest cleans up
`tmp_path` automatically.

---

### `tests/conftest.py`

```python
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
```

---

### `tests/test_auth.py`

| Test | Description |
|------|-------------|
| `test_login_success` | Valid admin credentials → 200 + `{"ok": true}`, session set |
| `test_login_wrong_password` | Wrong password → 401 |
| `test_login_nonexistent_user` | Unknown username → 401 |
| `test_login_no_password_set` | User row exists but `password_hash` is NULL → 401 |
| `test_logout_authenticated` | `POST /api/logout` while logged in → 200 + `{"ok": true}` |
| `test_logout_unauthenticated` | `POST /api/logout` without a session → 401 |

For `test_login_no_password_set`: insert a user row with `password_hash = NULL` directly
via `get_db()` inside an `app.app_context()`, then attempt to log in.

---

### `tests/test_users.py`

| Test | Description |
|------|-------------|
| `test_list_users_as_admin` | `GET /api/users` as admin → 200, list contains the admin row |
| `test_list_users_unauthenticated` | `GET /api/users` → 401 |
| `test_list_users_as_non_admin` | `GET /api/users` as a regular user → 403 |
| `test_create_user` | `POST /api/users {"username": "alice"}` → 201, user object returned with active invite |
| `test_create_user_duplicate` | `POST /api/users` with an already-existing username → 409 |
| `test_create_user_empty_username` | `POST /api/users {"username": ""}` → 400 |
| `test_reset_user` | `POST /api/users/<id>/reset` → 200, `has_password` is false, invite is non-null |
| `test_reset_admin_forbidden` | `POST /api/users/<admin_id>/reset` → 403 |
| `test_reset_nonexistent_user` | `POST /api/users/9999/reset` → 404 |
| `test_delete_user` | `DELETE /api/users/<id>` → 200 + `{"ok": true}` |
| `test_delete_admin_forbidden` | `DELETE /api/users/<admin_id>` → 403 |
| `test_delete_nonexistent_user` | `DELETE /api/users/9999` → 404 |

For tests that need a non-admin user: call `POST /api/users` via `admin_client` to
create the user, then read the returned `id`. The returned user object also contains the
invite token, which is useful in invite tests.

For `test_list_users_as_non_admin`: create a user, set their password via `POST
/api/invite/<token>`, then log in as that user, then attempt `GET /api/users`.

---

### `tests/test_invite.py`

| Test | Description |
|------|-------------|
| `test_get_invite_valid` | `GET /api/invite/<token>` with a live token → 200, `{"username": "alice"}` |
| `test_get_invite_expired` | Same but token's `expires` is in the past → 403 |
| `test_get_invite_invalid_token` | `GET /api/invite/bogustoken` → 403 |
| `test_redeem_invite_success` | `POST /api/invite/<token>` with matching 8-char passwords → 200 + `{"ok": true}` |
| `test_redeem_invite_clears_session` | After redemption, `GET /api/users` returns 401 (session wiped) |
| `test_redeem_invite_password_mismatch` | `password != confirm` → 400 |
| `test_redeem_invite_too_short` | `len(password) < 8` → 400 |
| `test_redeem_invite_expired` | Expired token → 403 |
| `test_redeem_invite_consumes_token` | After a successful POST, a second POST with the same token → 403 |
| `test_full_invite_flow` | Create user → get token → set password → log in with new credentials → 200 |

**Creating expired tokens for tests:** patch `nautilus_web_portal.api.time.time` using
`unittest.mock.patch` to return a value 8 days in the future (past the 7-day TTL).
No DB access required — the API's own expiry check sees the token as expired.

---

## Implementation Order

1. Edit `pyproject.toml` → run `uv add --group dev pytest` to regenerate `uv.lock`.
2. Create `nautilus_web_portal/` directory with `__init__.py`, then move `db.py`,
   `api.py`, `views.py` into it (updating imports).
3. Move `templates/` into `nautilus_web_portal/templates/`.
4. Update root `app.py`.
5. Update `Dockerfile`.
6. Delete now-redundant root-level `api.py`, `views.py`, `db.py`, `templates/`.
7. Create `tests/conftest.py`, `tests/test_auth.py`, `tests/test_users.py`,
   `tests/test_invite.py`.
8. Run `uv run --group dev pytest` and iterate until all tests pass.
9. Do a final `docker compose up --build` smoke test.
10. Commit everything.
