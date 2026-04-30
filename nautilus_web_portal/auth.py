import secrets
import time
from functools import wraps

from flask import Blueprint, g, jsonify, request
from werkzeug.security import check_password_hash

from .db import get_db

auth_bp = Blueprint("auth", __name__, url_prefix="/api")

TOKEN_TTL = 24 * 3600


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
        db.execute(
            "UPDATE auth_tokens SET expires_at = unixepoch() + ? WHERE token = ?",
            (TOKEN_TTL, token),
        )
        db.commit()
        g.current_user = row
        g.auth_token = token
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if g.current_user["username"] != "admin":
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated


@auth_bp.route("/me", methods=["GET"])
@login_required
def me():
    u = g.current_user
    return jsonify({
        "id": u["id"],
        "username": u["username"],
        "is_admin": u["username"] == "admin",
    })


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    if (
        not user
        or not user["password_hash"]
        or not check_password_hash(user["password_hash"], password)
    ):
        return jsonify({"error": "Invalid username or password"}), 401

    db.execute(
        "DELETE FROM auth_tokens WHERE user_id = ? AND expires_at <= unixepoch()",
        (user["id"],),
    )
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO auth_tokens (user_id, token, expires_at) VALUES (?, ?, unixepoch() + ?)",
        (user["id"], token, TOKEN_TTL),
    )
    db.commit()

    resp = jsonify({"ok": True})
    resp.set_cookie(
        "auth_token",
        token,
        httponly=True,
        samesite="Strict",
        max_age=30 * 24 * 3600,
    )
    return resp


@auth_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    db = get_db()
    db.execute("DELETE FROM auth_tokens WHERE token = ?", (g.auth_token,))
    db.commit()
    resp = jsonify({"ok": True})
    resp.delete_cookie("auth_token")
    return resp
