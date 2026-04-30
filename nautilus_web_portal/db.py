import os
import sqlite3

from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
        if current_app.config.get("TESTING"):
            g.db.execute("PRAGMA synchronous = OFF")
            g.db.execute("PRAGMA journal_mode = MEMORY")
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
    if current_app.config.get("TESTING"):
        db.execute("PRAGMA synchronous = OFF")
        db.execute("PRAGMA journal_mode = MEMORY")
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
    db.execute("""
        CREATE TABLE IF NOT EXISTS auth_tokens (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token      TEXT    UNIQUE NOT NULL,
            created_at REAL    NOT NULL DEFAULT (unixepoch()),
            expires_at REAL    NOT NULL
        )
    """)
    db.commit()

    admin_password = current_app.config.get("ADMIN_PASSWORD")
    admin = db.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()

    hash_method = current_app.config.get("HASH_METHOD", "scrypt")
    if admin and admin_password:
        db.execute(
            "UPDATE users SET password_hash = ? WHERE username = 'admin'",
            (generate_password_hash(admin_password, method=hash_method),),
        )
        db.commit()
    elif not admin and admin_password:
        db.execute(
            "INSERT INTO users (username, password_hash) VALUES ('admin', ?)",
            (generate_password_hash(admin_password, method=hash_method),),
        )
        db.commit()
    elif not admin:
        raise RuntimeError(
            "ADMIN_PASSWORD environment variable is required on first run "
            "(no admin account exists yet)."
        )
    # admin exists, ADMIN_PASSWORD absent → leave password unchanged

    db.close()
