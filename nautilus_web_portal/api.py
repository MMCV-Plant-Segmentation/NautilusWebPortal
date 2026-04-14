import secrets
import sqlite3
import time
from functools import wraps

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db

api_bp = Blueprint("api", __name__, url_prefix="/api")

INVITE_TTL = 7 * 24 * 3600  # 7 days


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Not logged in"}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("username") != "admin":
            return jsonify({"error": "Forbidden"}), 403
        return f(*args, **kwargs)
    return decorated


def _user_object(user, db):
    """Build the JSON representation of a user, including their active invite if any."""
    invite = db.execute(
        "SELECT token, expires FROM invite_codes "
        "WHERE user_id = ? AND expires > ? "
        "ORDER BY created_at DESC LIMIT 1",
        (user["id"], time.time()),
    ).fetchone()
    return {
        "id": user["id"],
        "username": user["username"],
        "has_password": user["password_hash"] is not None,
        "invite": (
            {"token": invite["token"], "expires": invite["expires"]}
            if invite else None
        ),
    }


@api_bp.route("/login", methods=["POST"])
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
    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return jsonify({"ok": True})


@api_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    session.clear()
    return jsonify({"ok": True})


@api_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def list_users():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at").fetchall()
    return jsonify([_user_object(u, db) for u in users])


@api_bp.route("/users", methods=["POST"])
@login_required
@admin_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username cannot be empty"}), 400
    db = get_db()
    try:
        db.execute("INSERT INTO users (username) VALUES (?)", (username,))
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username already exists"}), 409
    user = db.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    token = secrets.token_urlsafe(32)
    db.execute(
        "INSERT INTO invite_codes (user_id, token, expires) VALUES (?, ?, ?)",
        (user["id"], token, time.time() + INVITE_TTL),
    )
    db.commit()
    return jsonify(_user_object(user, db)), 201


@api_bp.route("/users/<int:user_id>/reset", methods=["POST"])
@login_required
@admin_required
def reset_user(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user["username"] == "admin":
        return jsonify({
            "error": "Admin password is managed via the ADMIN_PASSWORD environment variable"
        }), 403
    token = secrets.token_urlsafe(32)
    db.execute("UPDATE users SET password_hash = NULL WHERE id = ?", (user_id,))
    db.execute(
        "INSERT INTO invite_codes (user_id, token, expires) VALUES (?, ?, ?)",
        (user_id, token, time.time() + INVITE_TTL),
    )
    db.commit()
    user = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return jsonify(_user_object(user, db))


@api_bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_user(user_id):
    db = get_db()
    user = db.execute("SELECT username FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    if user["username"] == "admin":
        return jsonify({"error": "Cannot delete admin"}), 403
    db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return jsonify({"ok": True})


@api_bp.route("/invite/<token>", methods=["GET"])
def get_invite(token):
    db = get_db()
    row = db.execute(
        "SELECT invite_codes.expires, users.username "
        "FROM invite_codes JOIN users ON invite_codes.user_id = users.id "
        "WHERE invite_codes.token = ?",
        (token,),
    ).fetchone()
    if not row or row["expires"] < time.time():
        return jsonify({"error": "Invalid or expired invite link"}), 403
    return jsonify({"username": row["username"]})


@api_bp.route("/invite/<token>", methods=["POST"])
def redeem_invite(token):
    data = request.get_json(silent=True) or {}
    password = data.get("password", "")
    confirm = data.get("confirm", "")
    db = get_db()
    row = db.execute(
        "SELECT invite_codes.id, invite_codes.expires, users.id AS user_id "
        "FROM invite_codes JOIN users ON invite_codes.user_id = users.id "
        "WHERE invite_codes.token = ?",
        (token,),
    ).fetchone()
    if not row or row["expires"] < time.time():
        return jsonify({"error": "Invalid or expired invite link"}), 403
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(password), row["user_id"]),
    )
    db.execute("DELETE FROM invite_codes WHERE id = ?", (row["id"],))
    db.commit()
    session.clear()
    return jsonify({"ok": True})
