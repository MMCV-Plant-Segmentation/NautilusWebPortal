from flask import Blueprint, redirect, render_template, session, url_for

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    if "user_id" not in session:
        return redirect(url_for("views.login"))
    return render_template("index.html")


@views_bp.route("/login")
def login():
    if "user_id" in session:
        return redirect(url_for("views.index"))
    return render_template("login.html")


@views_bp.route("/admin")
def admin():
    if "user_id" not in session:
        return redirect(url_for("views.login"))
    if session.get("username") != "admin":
        return redirect(url_for("views.index"))
    return render_template("admin.html")


@views_bp.route("/invite/<token>")
def invite(token):
    return render_template("invite.html", token=token)
