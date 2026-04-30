# SPA Rewrite

Replace server-rendered Jinja templates with a React + MUI SPA. This is a prerequisite for the kubeconfig upload feature, which assumes this migration is already done.

## Stack

| Layer | Choice |
|---|---|
| Frontend framework | React 19 + TypeScript |
| UI components | MUI v6 |
| Build tool | Vite |
| Routing | React Router v6 |
| Frontend tests | None for now |
| Real-time | WebSockets via `flask-sock` |
| Auth | Opaque token, HttpOnly + SameSite=Strict cookie |

## Project layout

```
NautilusWebPortal/
  frontend/               ← new
    Dockerfile            ← Node 22 alpine build stage
    package.json
    tsconfig.json
    vite.config.ts
    src/
      main.tsx
      App.tsx
      api.ts              ← typed fetch helpers, all API calls go here
      auth/
        AuthContext.tsx
        useAuth.ts
      pages/
        LoginPage.tsx
        HomePage.tsx
        AdminPage.tsx
        InvitePage.tsx    ← stub; filled in by kubeconfig feature
      hooks/
        useWebSocket.ts   ← reusable WS hook
  nautilus_web_portal/    ← existing Python package
  tests/                  ← existing Python tests
```

## Auth model

Server-side sessions are replaced by an opaque token stored in the DB and delivered as an HttpOnly, SameSite=Strict cookie. The client never touches the token directly.

```sql
CREATE TABLE IF NOT EXISTS auth_tokens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token      TEXT    UNIQUE NOT NULL,
    created_at REAL    NOT NULL DEFAULT (unixepoch()),
    expires_at REAL    NOT NULL
);
```

Token TTL: 24 hours, sliding. Every authenticated request bumps `expires_at` by another 24 hours, so active sessions stay alive indefinitely. Cleanup of expired rows happens lazily on login.

### New/changed endpoints

| Method | Path | Auth | Notes |
|---|---|---|---|
| `POST` | `/api/login` | — | Creates token row, sets cookie |
| `POST` | `/api/logout` | cookie | Deletes token row, clears cookie |
| `GET` | `/api/me` | cookie | Returns `{id, username, is_admin}` or 401 |

All existing endpoints keep their paths; only the auth mechanism changes (`session` → cookie lookup).

### Auth decorator replacement

```python
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.cookies.get("auth_token")
        if not token:
            return jsonify({"error": "Not logged in"}), 401
        db = get_db()
        row = db.execute(
            "SELECT users.id, users.username FROM auth_tokens "
            "JOIN users ON auth_tokens.user_id = users.id "
            "WHERE auth_tokens.token = ? AND auth_tokens.expires_at > unixepoch()",
            (token,),
        ).fetchone()
        if not row:
            return jsonify({"error": "Not logged in"}), 401
        g.current_user = row
        return f(*args, **kwargs)
    return decorated
```

`admin_required` checks `g.current_user["username"] == "admin"` instead of `session`.

## Frontend auth flow

On app mount, React calls `GET /api/me`. A 200 means logged in; a 401 means not. The result is stored in `AuthContext` and consumed via `useAuth()`. React Router redirects unauthenticated users to `/login`.

`api.ts` wraps `fetch` so every call includes `credentials: 'include'` (required for cross-origin cookie forwarding in dev). A 401 response from *any* endpoint clears the auth context and redirects to `/login` — so a genuinely expired token is handled gracefully no matter which call triggers it.

## WebSocket plumbing

`flask-sock` is added as a Python dependency. A single multiplexed endpoint handles all streaming:

```
GET /ws  (WebSocket upgrade)
```

Messages use a simple JSON envelope:

```json
{ "channel": "admin_logs", "data": "..." }
```

The server pushes to whichever channels the client has subscribed to. Channels defined now: none — the endpoint is wired up but no channels are active until the kubeconfig feature adds them.

`useWebSocket.ts` on the frontend is a React hook that opens the connection once and lets components subscribe by channel name.

## Flask catch-all (production)

`views.py` is stripped to a single route that serves the built frontend:

```python
@views_bp.route("/", defaults={"path": ""})
@views_bp.route("/<path:path>")
def catch_all(path):
    dist = Path(current_app.root_path).parent / "frontend" / "dist"
    file = dist / path
    if file.is_file():
        return send_from_directory(dist, path)
    return send_from_directory(dist, "index.html")
```

Static assets (JS/CSS chunks) are served directly; everything else gets `index.html` so React Router handles the route.

## Dev workflow

Two processes run simultaneously:

```
flask run          # port 5000
cd frontend && npm run dev   # port 5173
```

`vite.config.ts` proxies API and WebSocket traffic:

```ts
server: {
  proxy: {
    '/api': 'http://localhost:5000',
    '/ws':  { target: 'ws://localhost:5000', ws: true },
  }
}
```

Browser points at `http://localhost:5173`. Flask never serves HTML in dev.

## Dockerfile

The frontend build lives in its own `frontend/Dockerfile` (Node 22 alpine), separate from the main `Dockerfile` (Ubuntu only). `docker-bake.hcl` wires them together via Docker Bake:

```hcl
target "frontend" {
  context    = "./frontend"
  dockerfile = "Dockerfile"
}

target "app" {
  context  = "."
  contexts = {
    frontend-build = "target:frontend"
  }
  tags = ["nautiluswebportal-nwp:latest"]
}
```

`target:frontend` tells Bake to fully build the `frontend` target first and make its output available as a named context called `frontend-build`. The main `Dockerfile` is single-stage Ubuntu; it references that context only in the final copy:

```dockerfile
FROM ubuntu:26.04
...
COPY --from=frontend-build /app/dist ./frontend/dist
CMD [...]
```

`compose.yaml` references the pre-built image by name (`image: nautiluswebportal-nwp:latest`) rather than triggering a build itself. BuildKit caches each target independently by content, so Python dependency layers survive frontend-only changes and vice versa.

Build command:

```sh
docker buildx bake && docker compose up
```

## Pages (current scope)

| Page | Route | Auth | Notes |
|---|---|---|---|
| `LoginPage` | `/login` | — | Redirect to `/` if already logged in |
| `HomePage` | `/` | required | Placeholder; fleshed out later |
| `AdminPage` | `/admin` | admin | User table + settings; matches existing `admin.html` behaviour |
| `InvitePage` | `/invite/:token` | — | Stub only; three-phase wizard added by kubeconfig feature |

## Implementation order

1. Add `flask-sock` to `pyproject.toml`, run `uv sync`
2. Add `frontend/` scaffold: `npm create vite@latest`, add React Router, MUI, configure `vite.config.ts` proxy
3. DB migration: add `auth_tokens` table to `init_db()`
4. Replace `login_required` / `admin_required` decorators; update `POST /api/login`, `POST /api/logout`; add `GET /api/me`; remove `session` usage from all endpoints
5. Wire up `flask-sock` `/ws` endpoint (no active channels yet)
6. React app shell: `AuthContext`, `useAuth`, routing skeleton, `api.ts` with `credentials: 'include'`
7. `LoginPage` — replaces `login.html`
8. `HomePage` — replaces `index.html`
9. `AdminPage` — replaces `admin.html` (user table + settings with optimistic concurrency UI)
10. `InvitePage` stub — single "invite link loaded" state; wizard phases added later
11. `useWebSocket` hook wired to `/ws`; smoke-test connection in browser devtools
12. Add `frontend/Dockerfile` for the Node build; add `docker-bake.hcl`; update `compose.yaml` to use `image:`; update main `Dockerfile` to single-stage Ubuntu with `COPY --from=frontend-build`
13. Update Flask `views.py` to catch-all; delete `nautilus_web_portal/templates/`
14. Commit
