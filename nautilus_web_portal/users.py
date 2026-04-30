import secrets
import sqlite3
import time

from flask import Blueprint, jsonify, request

from .auth import admin_required, login_required
from .db import get_db

users_bp = Blueprint("users", __name__, url_prefix="/api")

INVITE_TTL = 7 * 24 * 3600


def _user_object(user, db):
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


@users_bp.route("/users", methods=["GET"])
@login_required
@admin_required
def list_users():
    db = get_db()
    users = db.execute("SELECT * FROM users ORDER BY created_at").fetchall()
    return jsonify([_user_object(u, db) for u in users])


@users_bp.route("/users", methods=["POST"])
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


@users_bp.route("/users/<int:user_id>/reset", methods=["POST"])
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


@users_bp.route("/users/<int:user_id>", methods=["DELETE"])
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
