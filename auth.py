"""
auth.py — Unix socket auth listener + Flask login route

Flow:
  1. Background thread listens on a Unix domain socket at SOCKET_PATH
  2. nwp-auth (running on the host as some user) connects to the socket
  3. Flask reads SO_PEERCRED to get the connecting process's UID
  4. Flask generates a one-time token, stores uid -> token, sends back a login URL
  5. User opens the URL; /login validates the token and sets session["uid"]
"""

import os
import secrets
import socket
import struct
import threading
import time
from functools import wraps

from flask import abort, redirect, request, session, url_for

SOCKET_PATH = "/home/ubuntu/nwp/auth.sock"
PORTAL_URL = "http://localhost:8080"
TOKEN_TTL = 60  # seconds

_pending = {}   # token -> (uid, expires_at)
_lock = threading.Lock()


def _serve():
    os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
    try:
        os.unlink(SOCKET_PATH)
    except FileNotFoundError:
        pass

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as srv:
        srv.bind(SOCKET_PATH)
        os.chmod(SOCKET_PATH, 0o666)  # world-connectable; SO_PEERCRED tells us who
        srv.listen()
        while True:
            conn, _ = srv.accept()
            with conn:
                cred_size = struct.calcsize("3i")
                raw = conn.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, cred_size)
                _pid, uid, _gid = struct.unpack("3i", raw)

                token = secrets.token_urlsafe(32)
                expires_at = time.time() + TOKEN_TTL

                with _lock:
                    # Drop any expired tokens while we're here
                    now = time.time()
                    expired = [t for t, (_, exp) in _pending.items() if exp < now]
                    for t in expired:
                        del _pending[t]

                    _pending[token] = (uid, expires_at)

                url = f"{PORTAL_URL}/login?token={token}\n"
                conn.sendall(url.encode())


def start_auth_listener():
    t = threading.Thread(target=_serve, daemon=True)
    t.start()


def pop_token(token):
    """Return uid if token is valid and unexpired, else None. Consumes the token."""
    with _lock:
        entry = _pending.pop(token, None)
    if entry is None:
        return None
    uid, expires_at = entry
    if time.time() > expires_at:
        return None
    return uid


def login_route():
    token = request.args.get("token", "")
    uid = pop_token(token)
    if uid is None:
        abort(403)
    session["uid"] = uid
    return redirect(url_for("index"))


def logout_route():
    session.clear()
    return redirect(url_for("index"))


def require_login(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "uid" not in session:
            abort(403)
        return f(*args, **kwargs)
    return decorated
