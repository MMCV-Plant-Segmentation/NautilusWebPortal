import os

from flask import Flask
from flask_sock import Sock


def create_app(test_config=None):
    app = Flask(__name__)

    if test_config is None:  # pragma: no cover
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
        app.config["DATABASE"] = os.path.expanduser("~/nwp/db.sqlite3")
        app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD")
    else:
        app.config.update(test_config)

    from .db import close_db, init_db
    from .auth import auth_bp
    from .users import users_bp
    from .invites import invites_bp
    from .views import views_bp

    app.teardown_appcontext(close_db)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(invites_bp)
    app.register_blueprint(views_bp)

    with app.app_context():
        if test_config is None:  # pragma: no cover
            init_db()

    sock = Sock(app)

    @sock.route("/ws")
    def websocket(ws):  # pragma: no cover
        try:
            while True:
                ws.receive(timeout=60)
        except Exception:
            pass

    return app
