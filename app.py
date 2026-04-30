import os

from nautilus_web_portal import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ["PORT"]), debug=False)
