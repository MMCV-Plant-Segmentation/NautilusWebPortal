import time

from flask import Blueprint, current_app, jsonify, request
from werkzeug.security import generate_password_hash

from .db import get_db

invites_bp = Blueprint("invites", __name__, url_prefix="/api")


def _clear_caller_auth(db) -> None:
    token = request.cookies.get("auth_token")
    if token:
        db.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        db.commit()


@invites_bp.route("/invite/<token>", methods=["GET"])
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
    _clear_caller_auth(db)
    resp = jsonify({"username": row["username"]})
    resp.delete_cookie("auth_token")
    return resp


@invites_bp.route("/invite/<token>", methods=["POST"])
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
        (generate_password_hash(password, method=current_app.config.get("HASH_METHOD", "scrypt")), row["user_id"]),
    )
    db.execute("DELETE FROM invite_codes WHERE id = ?", (row["id"],))
    db.commit()
    _clear_caller_auth(db)
    resp = jsonify({"ok": True})
    resp.delete_cookie("auth_token")
    return resp
