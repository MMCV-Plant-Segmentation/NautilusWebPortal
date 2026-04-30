from pathlib import Path

from flask import Blueprint, current_app, send_from_directory

views_bp = Blueprint("views", __name__)


@views_bp.route("/", defaults={"path": ""})
@views_bp.route("/<path:path>")
def catch_all(path: str):  # pragma: no cover
    dist = Path(current_app.root_path).parent / "frontend" / "dist"
    file = dist / path
    if file.is_file():
        return send_from_directory(dist, path)
    return send_from_directory(dist, "index.html")
