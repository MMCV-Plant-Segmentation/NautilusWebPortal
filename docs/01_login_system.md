# Login System Implementation Plan

## Overview

Add a username/password login system to the NautilusWebPortal Flask app, with an admin
panel for managing users via invite links. The API is isolated under `/api/` from the
start so that the frontend can be swapped for a React SPA later without touching the
backend.

---

## File Structure

```
NautilusWebPortal/
├── pyproject.toml          NEW
├── uv.lock                 NEW (generated, committed to git)
├── compose.yaml            NEW
├── app.py                  NEW — creates Flask app, registers blueprints, calls init_db()
├── api.py                  NEW — Blueprint mounted at /api/ (all JSON endpoints)
├── views.py                NEW — Blueprint mounted at / (serves HTML templates)
├── db.py                   NEW — init_db(), get_db(), close_db()
├── templates/
│   ├── base.html           NEW
│   ├── index.html          NEW — placeholder home page
│   ├── login.html          NEW
│   ├── admin.html          NEW
│   ├── invite.html         NEW — set-password form
│   └── invite_invalid.html NEW — shown for expired/invalid tokens
├── Dockerfile              MODIFIED
├── kubewrapper.py          UNCHANGED
└── README.md               UNCHANGED
```

`.env` is created manually by the operator and never committed to git:
```
ADMIN_PASSWORD=<generated>
SECRET_KEY=<generated>
PORT=5000
```
Generate values with: `python3 -c "import secrets; print(secrets.token_urlsafe(20))"`

Add `.env` to `.gitignore`. Docker Compose automatically reads `.env` for variable
substitution in `compose.yaml` (e.g. `${PORT}` in the ports mapping), and `env_file: .env`
passes the same variables to Flask — single source of truth, no duplication.

---

## Database Schema

SQLite at `~/nwp/db.sqlite3`. Inside the container `~` is `/home/ubuntu`, so the full
path is `/home/ubuntu/nwp/db.sqlite3`. The `nwp-data` Docker volume is mounted at
`/home/ubuntu/nwp`, so the database persists across container rebuilds.

```sql
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    UNIQUE NOT NULL,
    password_hash TEXT,        -- NULL until the user sets a password via invite link
    created_at    REAL    NOT NULL DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS invite_codes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT    UNIQUE NOT NULL,
    expires    REAL    NOT NULL,
    created_at REAL    NOT NULL DEFAULT (unixepoch())
);
```

Notes:
- Passwords are hashed with `werkzeug.security.generate_password_hash` (scrypt).
- Tokens are `secrets.token_urlsafe(32)`.
- Invite TTL is **7 days** (604800 seconds).
- "Current active invite" for a user = `SELECT * FROM invite_codes WHERE user_id = ?
  AND expires > unixepoch() ORDER BY created_at DESC LIMIT 1`.
- "Reset password" = INSERT a new invite_codes row (old rows expire naturally).
- The admin account (`username = 'admin'`) is managed exclusively via the `ADMIN_PASSWORD`
  env var. It never uses invite links and cannot be deleted or reset via the UI.

---

## Environment Variables

| Variable         | Required     | Description |
|------------------|--------------|-------------|
| `ADMIN_PASSWORD` | Always       | Admin's password. On every startup, if this var is set, the admin's hash in the DB is updated to match — so changing the var and restarting is all that's needed to change the admin password. If the var is absent and no admin row exists yet, the app raises `RuntimeError`. If the var is absent but an admin row already exists, startup proceeds normally (password unchanged). |
| `SECRET_KEY`     | Always       | Flask session signing key. Must be stable across restarts (changing it invalidates all sessions). |
| `PORT`           | Always       | Port Flask binds to inside the container (e.g. `5000`). |

---

## `pyproject.toml`

Standard uv project file. Run `uv init` then `uv add flask` to generate it.

```toml
[project]
name = "nautilus-web-portal"
version = "0.1.0"
dependencies = ["flask"]
```

`kubewrapper.py` is stdlib-only; it stays as a standalone script outside the uv project.

Commit `uv.lock` to git for reproducible Docker builds.

---

## `compose.yaml`

```yaml
services:
  nwp:
    build: .
    ports:
      - "${PORT}:${PORT}"
    volumes:
      - nwp-data:/home/ubuntu/nwp
    env_file: app.env

volumes:
  nwp-data:
```

**Resetting the database** (e.g. during development):
```sh
docker compose down -v   # destroys nwp-data volume
docker compose up --build
```

---

## `Dockerfile` Changes

Add after the existing `uv` install step, in this order (for layer caching):

1. `COPY pyproject.toml uv.lock ./` then `RUN uv sync --frozen`
2. `COPY app.py api.py views.py db.py ./`
3. `COPY templates/ ./templates/`
4. `CMD ["uv", "run", "python", "app.py"]`

The existing kubectl/kubelogin/kubewrapper steps are unchanged.

---

## `db.py`

### `init_db()`

1. `os.makedirs(os.path.expanduser("~/nwp"), exist_ok=True)`
2. Run both `CREATE TABLE IF NOT EXISTS` statements.
3. Admin password sync logic:
   - Read `ADMIN_PASSWORD` from env (may be absent).
   - If admin row exists and `ADMIN_PASSWORD` is set: `UPDATE users SET password_hash = ?
     WHERE username = 'admin'` with the freshly hashed value. This is how the admin
     password is changed — update the env var and restart.
   - If admin row does not exist and `ADMIN_PASSWORD` is set: INSERT the admin row with
     the hashed password.
   - If admin row does not exist and `ADMIN_PASSWORD` is absent: raise `RuntimeError`.
   - If admin row exists and `ADMIN_PASSWORD` is absent: do nothing (password unchanged).

### `get_db()` / `close_db()`

Standard Flask `g`-based pattern: open connection on first call per request, set
`row_factory = sqlite3.Row`, cache in `g.db`. `teardown_appcontext` closes it.

---

## `app.py`

- Creates the Flask app.
- Reads `SECRET_KEY` and `PORT` from env (raise `KeyError` / clear error if missing).
- Registers `api_bp` at `/api` and `views_bp` at `/`.
- Calls `init_db()` then `app.run(host="0.0.0.0", port=int(PORT))` in
  `if __name__ == "__main__"`.

---

## `api.py` — JSON API Blueprint

Mounted at `/api`. All responses are JSON. Auth state is managed via Flask sessions
(cookie-based; works identically for traditional HTML pages and a future React SPA since
both run on the same origin).

### Auth helpers

- `login_required` decorator: if `session.get("user_id")` is absent, return
  `{"error": "not logged in"}, 401`.
- `admin_required` decorator: if `session.get("username") != "admin"`, return
  `{"error": "forbidden"}, 403`.

### Endpoints

| Method | Path                          | Auth  | Request body (JSON)         | Success response |
|--------|-------------------------------|-------|-----------------------------|------------------|
| POST   | `/api/login`                  | —     | `{username, password}`      | `{"ok": true}` + sets session |
| POST   | `/api/logout`                 | login | —                           | `{"ok": true}` + clears session |
| GET    | `/api/users`                  | admin | —                           | Array of user objects (see below) |
| POST   | `/api/users`                  | admin | `{username}`                | Created user object |
| POST   | `/api/users/<id>/reset`       | admin | —                           | Updated user object |
| DELETE | `/api/users/<id>`             | admin | —                           | `{"ok": true}` |
| GET    | `/api/invite/<token>`         | —     | —                           | `{"username": "..."}` or 403 |
| POST   | `/api/invite/<token>`         | —     | `{password, confirm}`       | `{"ok": true}` or error |

**User object shape** (returned by GET `/api/users` and POST `/api/users`):
```json
{
  "id": 1,
  "username": "alice",
  "has_password": true,
  "invite": {
    "token": "...",
    "expires": 1234567890.0
  }
}
```
`invite` is `null` if there is no active (unexpired) invite. `has_password` is a boolean
derived from whether `password_hash` is non-null — the hash itself is never sent to the
client.

**`POST /api/login` logic:**
- Look up user by username. Check `password_hash` is non-null and passes
  `check_password_hash`. On any failure: `{"error": "Invalid username or password"}, 401`
  (same message regardless of which field was wrong).
- On success: `session["user_id"] = user["id"]`, `session["username"] = user["username"]`.

**`POST /api/users` logic:**
- Reject blank username.
- INSERT into `users`. Catch `IntegrityError` → `{"error": "Username already exists"}, 409`.
- INSERT into `invite_codes` with `token = secrets.token_urlsafe(32)`,
  `expires = time.time() + 604800`.
- Return the new user object.

**`POST /api/users/<id>/reset` logic:**
- If the target user is admin: return `{"error": "Admin password is managed via the
  ADMIN_PASSWORD environment variable"}, 403`.
- INSERT a new row into `invite_codes` (a new token + 7-day expiry). Old codes for this
  user are left to expire naturally.
- SET `users.password_hash = NULL` for this user.
- Return the updated user object.

**`DELETE /api/users/<id>` logic:**
- Look up user. If `username == 'admin'`: `{"error": "Cannot delete admin"}, 403`.
- `DELETE FROM users WHERE id = ?` (cascades to `invite_codes`).

**`GET /api/invite/<token>` and `POST /api/invite/<token>` logic:**
- Look up row in `invite_codes` by token. If not found or `expires < time.time()`:
  `{"error": "Invalid or expired invite link"}, 403`.
- GET: return `{"username": user["username"]}`.
- POST: validate `password == confirm` and `len(password) >= 8`. On failure return
  `{"error": "..."}`. On success:
  - `UPDATE users SET password_hash = ? WHERE id = ?`
  - `DELETE FROM invite_codes WHERE id = ?` (consume the token)
  - Return `{"ok": true}`.

---

## `views.py` — HTML Blueprint

Mounted at `/`. Serves Jinja2 templates. Each page makes `fetch()` calls to `/api/`
for any action; there are no HTML form POSTs in the traditional sense.

When the frontend is later replaced with a React SPA, this blueprint is replaced with a
single catch-all route that serves the built `index.html`.

| Route         | Template             | Notes |
|---------------|----------------------|-------|
| `/login`      | `login.html`         | Redirect to `/` if already logged in |
| `/logout`     | —                    | Calls `POST /api/logout` then redirects to `/login` (can be a plain link) |
| `/`           | `index.html`         | Placeholder; redirect to `/login` if not logged in |
| `/admin`      | `admin.html`         | Redirect to `/` if not admin |
| `/invite/<token>` | `invite.html` or `invite_invalid.html` | Check token validity via `GET /api/invite/<token>` |

---

## Templates

Plain HTML/CSS, no external dependencies. All extend `base.html`.

### `base.html`
- `<title>` block.
- Simple nav: app name left, username + logout link right (if logged in), admin panel
  link if on a non-admin page and user is admin.
- Flash/error message area (populated by JS, not Flask's `flash()`).
- `{% block content %}{% endblock %}`.

### `login.html`
- Username + password inputs.
- JS intercepts submit → `POST /api/login` → redirect to `/` on success, show error on failure.

### `admin.html`
- "Create user" form: username input + button → `POST /api/users` → refresh table.
- Table of users populated by `GET /api/users` on page load.

**Table columns:**
- **Username**
- **Status:**
  - `has_password == true` → "Active"
  - `invite != null` → "Invite pending — expires in Xd Xh", the raw token in a
    `<code>` block, and two buttons: "Copy code" (copies the bare token) and "Copy link"
    (copies `window.location.origin + "/invite/" + invite.token`). The code is the
    reliable share mechanism since recipients may be forwarding a different local port
    via SSH tunnel; the link is a convenience for when ports happen to match.
  - `invite == null && !has_password` → "No invite"
- **Actions (both hidden for admin row):**
  - "Reset password" button → `POST /api/users/<id>/reset` → refresh row
  - "Delete" button → `DELETE /api/users/<id>` → remove row

### `invite.html`
- Greet user by username (fetched from `GET /api/invite/<token>` on load).
- Password + confirm inputs.
- JS submit → `POST /api/invite/<token>` → redirect to `/login` on success.

### `invite_invalid.html`
- Static message: link expired or invalid, contact the admin.

---

## README Updates (after implementation)

Add a "Running the app" section to `README.md` covering:
1. Creating `app.env` (with the `token_urlsafe` generation command for each value).
2. Adding `app.env` to `.gitignore`.
3. `docker compose up --build` to start.
4. How to access via SSH tunnel (the `-L` command).
5. How to reset the database: `docker compose down -v && docker compose up --build`.
6. How to change the admin password: update `ADMIN_PASSWORD` in `app.env` and restart
   (`docker compose restart` or `docker compose up`).

---

## Future: Switching to React

1. Build the React app (Vite + React + MUI) as a separate project.
2. Add a single catch-all route to `views.py`:
   ```python
   @views_bp.route("/", defaults={"path": ""})
   @views_bp.route("/<path:path>")
   def spa(path):
       return send_from_directory("static", "index.html")
   ```
3. Copy the Vite build output into `static/`.
4. The `/api/` Blueprint requires zero changes.
