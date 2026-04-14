import os

from nautilus_web_portal import create_app
from nautilus_web_portal.db import init_db

app = create_app()

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(host="0.0.0.0", port=int(os.environ["PORT"]), debug=False)
