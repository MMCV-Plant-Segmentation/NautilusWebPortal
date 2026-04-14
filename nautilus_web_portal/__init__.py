import os

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__)

    if test_config is None:
        app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
        app.config["DATABASE"] = os.path.expanduser("~/nwp/db.sqlite3")
        app.config["ADMIN_PASSWORD"] = os.environ.get("ADMIN_PASSWORD")
    else:
        app.config.update(test_config)

    from .db import close_db
    from .api import api_bp
    from .views import views_bp

    app.teardown_appcontext(close_db)
    app.register_blueprint(api_bp)
    app.register_blueprint(views_bp)
    return app
