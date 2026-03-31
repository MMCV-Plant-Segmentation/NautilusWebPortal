import os
from flask import Flask, session
from auth import login_route, logout_route, require_login, start_auth_listener

app = Flask(__name__)
app.secret_key = os.urandom(32)  # sessions don't survive restarts; that's fine

app.add_url_rule("/login", "login", login_route)
app.add_url_rule("/logout", "logout", logout_route)


@app.route("/")
@require_login
def index():
    return f"<h1>NWP Portal</h1><p>Logged in as UID {session['uid']}</p><a href='/logout'>Log out</a>"


if __name__ == "__main__":
    start_auth_listener()
    app.run(host="0.0.0.0", port=5000)
