# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

NautilusWebPortal is a Flask + React SPA for onboarding users to the NRP-Nautilus Kubernetes cluster. Users receive an invite link, upload a kubeconfig, complete OIDC device-code auth, and set a password. The admin manages users and cluster settings through an admin panel. See `docs/` for feature plans in implementation order.

---

## Commands

### Backend

```sh
uv sync --group dev          # install all dependencies including dev
uv run pytest                # run tests (fast — ~0.6s for 34 tests)
uv run pytest --cov          # run with coverage (source configured in pyproject.toml)
uv run pytest tests/test_auth.py::test_login_success   # run a single test
flask run                    # dev server on :5000 (requires .env)
```

### Frontend

```sh
cd frontend
npm install
npm run dev      # Vite dev server on :5173, proxies /api and /ws to :5000
npm run build    # production build → frontend/dist/
```

### Docker (production)

```sh
docker buildx bake           # build frontend + app images (must run before compose up)
docker compose up            # start the container; requires .env with SECRET_KEY, ADMIN_PASSWORD, PORT
docker compose down -v       # wipe the database volume
```

### Activate pre-commit hook (once per clone)

```sh
git config core.hooksPath .githooks
```

The hook runs `uv run pytest --cov --cov-fail-under=95` before every commit.

---

## Architecture

### Request flow

In development: browser → Vite (:5173) → proxies `/api/*` and `/ws` to Flask (:5000).  
In production: Flask serves `frontend/dist/` via a catch-all in `views.py`; all routes return `index.html` except exact static asset matches.

### Backend modules (`nautilus_web_portal/`)

Each domain area is its own Blueprint registered in `__init__.py`:

| File | Blueprint | URL prefix | Responsibility |
|------|-----------|------------|----------------|
| `auth.py` | `auth_bp` | `/api` | `login_required` / `admin_required` decorators; `/api/login`, `/api/logout`, `/api/me` |
| `users.py` | `users_bp` | `/api` | `/api/users` CRUD; imports decorators from `auth.py` |
| `invites.py` | `invites_bp` | `/api` | `/api/invite/<token>` GET and POST; `_clear_caller_auth` helper |
| `views.py` | `views_bp` | (none) | catch-all that serves `frontend/dist/` |
| `db.py` | — | — | `get_db()`, `close_db()`, `init_db()` |

`api.py` re-exports `auth_bp`, `users_bp`, `invites_bp`, `login_required`, `admin_required`, `TOKEN_TTL`, and `INVITE_TTL` for convenience. New API endpoints go in one of the domain modules above, or a new module following the same Blueprint pattern.

### Auth model

Opaque tokens stored in the `auth_tokens` DB table, delivered as an `HttpOnly + SameSite=Strict` cookie. `login_required` looks up the token on every request and slides the 24-hour TTL. Both invite endpoints (`GET` and `POST /api/invite/<token>`) clear the caller's auth token on the assumption that whoever is redeeming an invite shouldn't be a logged-in user.

### Frontend auth flow

`AuthContext` calls `GET /api/me` on mount to determine auth state. `api.me()` and `api.invite.get()` use plain `fetch` (not `apiFetch`) so a 401 from those two calls does **not** trigger the global redirect-to-login handler — that handler is installed only after the initial `/api/me` resolves. Every other `api.*` call uses `apiFetch`, which fires `onUnauthorized` on any 401.

### Docker build

Three separate Dockerfiles, combined by `docker-bake.hcl`:

| File | Base | Produces |
|------|------|----------|
| `frontend/Dockerfile` | Node 22 alpine | built React app (`/app/dist`) |
| `tools/Dockerfile` | Ubuntu 26.04 | `kubectl` + `kubectl-oidc_login` binaries, pinned via `ARG` |
| `Dockerfile` | Ubuntu 26.04 | final runtime image |

The main `Dockerfile` copies from both via `COPY --from=frontend-build` and `COPY --from=tools-build`. `compose.yaml` references the pre-built image by name (`image: nautiluswebportal-nwp:latest`). BuildKit caches each target independently by content — changing Python files does not invalidate the Node or tools cache, and vice versa. To pin-bump kubectl: change `KUBECTL_VERSION` in `tools/Dockerfile`.

### Testing

- Each test gets an isolated SQLite database via `tmp_path` in `conftest.py`
- `HASH_METHOD: pbkdf2:sha256:1` makes password hashing fast in tests
- `PRAGMA synchronous = OFF` + `PRAGMA journal_mode = MEMORY` eliminate fsync overhead
- Time-travel tests mock `nautilus_web_portal.invites.time.time` (not the old `api.time` path)
- Three branches carry `# pragma: no cover`: the production config block in `__init__.py`, the WebSocket handler stub, and `views.py`'s `catch_all` (untestable without a built `frontend/dist/`)

---

## Conventions

- **`git mv`** for renaming/moving files — not `rm` + re-add.
- **No Makefile.** All multi-step build logic lives in Docker or is a documented shell sequence.
- **TDD for new features.** Write tests first, then the code.
- **Don't implement until the plan is signed off.** For any non-trivial feature, present an approach and wait for explicit agreement before writing code.
- **Don't write planning docs without being asked what to plan.** Ask first.
- **Only commit docs for finished work.** A feature plan lives as an untracked file until the feature is implemented; commit the doc in the same commit as the code.
- **New API modules** follow the same pattern as `auth.py` / `users.py` / `invites.py`: one Blueprint per file, registered in `__init__.py`, decorators imported from `auth.py`.
