# Nautilus Web Portal

A web portal for submitting COLMAP jobs to the NRP-Nautilus Kubernetes cluster.

---

## Setup

### 1. Create `.env`

Copy the example below to `.env` in the project root and fill in the values.

```sh
SECRET_KEY=<random string>   # used to sign Flask session cookies (generated in the next step)
ADMIN_PASSWORD=<password>    # sets (or updates) the admin account password on startup
PORT=5000
```

Generate a secure random `SECRET_KEY`:

```sh
python3 -c "import secrets; print(secrets.token_hex(32))"
```

`.env` is never committed to git. Keep it safe.

### 2. Build and run

On the server, run:

```sh
docker buildx bake && docker compose up
```

`docker buildx bake` builds the frontend (Node) and app (Ubuntu) images separately and combines them. `docker compose up` starts the container using the image that was just built.

The app will listen on `PORT` inside and outside of the container. The database is stored in the `nwp-data` Docker volume (which persists across restarts).

### 3. Access via SSH tunnel

The app is not exposed to the network directly. Unless you are using the app from the server itself, you will need to forward it to your local machine:

```sh
ssh -L <local-port>:localhost:<PORT> <user>@<server>.rnet.missouri.edu
```

`PORT` is whatever is set in `.env` on the server. `local-port` can be anything free on
your machine — it does not need to match. Then open `http://localhost:<local-port>` in
your browser.

### 4. First login

Log in with:

- **Username:** `admin`
- **Password:** whatever you set for `ADMIN_PASSWORD` in `.env`

From the admin panel you can create additional users. Each new user gets an invite
code — copy it from the admin panel and send it to them. They can paste it into the
"Have an invite code?" box on the login page, or use the full invite link if they happen
to be forwarding the same local port as you.

---

## Common operations

### Change the admin password

Update `ADMIN_PASSWORD` in `.env` and restart:

```sh
docker buildx bake && docker compose up
```

The new password takes effect immediately on startup.

### Reset the database (wipe all data)

```sh
docker compose down -v
docker buildx bake && docker compose up
```

`-v` removes the `nwp-data` volume. A fresh database is created on next startup.

---

## Development

### Install dependencies (including test tools)

```sh
uv sync --group dev
```

### Activate the pre-commit hook

The repo ships a hook that runs the test suite with coverage before every commit. Activate it once after cloning:

```sh
git config core.hooksPath .githooks
```

### Run tests

```sh
uv run pytest
```

Tests use an isolated temporary SQLite file per test — no running container needed.

Run with coverage (what the pre-commit hook does):

```sh
uv run pytest --cov
```

### Run the app locally (without Docker)

```sh
SECRET_KEY=dev ADMIN_PASSWORD=devpass PORT=5000 uv run python app.py
```
