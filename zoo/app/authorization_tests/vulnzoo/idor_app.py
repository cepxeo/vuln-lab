"""A task board with sign-up, login and per-user objects, for the IDOR case.

Every user gets a session cookie at login. /tasks lists the user's own tasks
and links each one (/tasks/<id>); the vulnerable app answers /tasks/<id> to any
logged-in user, the safe twin only to its owner. The engagement session is
alice's; the engine registers a second account through the sign-up form.
"""
from __future__ import annotations

import secrets

from authorization_tests.vulnzoo.apps import _base
from authorization_tests.vulnzoo.server import App, Request, Response

ALICE_SESSION = "zoo-alice-session"

SIGNUP = ('<html><body><h1>Create account</h1><form method="post" action="/register">'
          '<input name="username"><input name="email"><input type="password" name="password">'
          '<button>Sign up</button></form></body></html>')
LOGIN = ('<html><body><h1>Sign in</h1><form method="post" action="/login"><input name="username">'
         '<input type="password" name="password"><button>Sign in</button></form></body></html>')


def build(safe: bool, variant: str) -> App:
    users = {"alice": {"password": "zoo-alice-password", "email": "alice@corp.example"}}
    sessions = {ALICE_SESSION: "alice"}
    tasks = {"101": {"owner": "alice", "title": "Quarterly payroll export", "note": "IBAN DE00 1234"}}
    app = _base(variant, title="Taskboard", links=("/login", "/register", "/tasks"))

    def user_of(request: Request) -> str:
        # A session cookie, or the same session token as a Bearer header (an
        # engagement given its session as a header).
        return sessions.get(request.cookie("sid"), "") or sessions.get(request.bearer(), "")

    def register(request: Request) -> Response:
        form = request.form()
        name = str(form.get("username") or "").strip()
        if not name or name in users or not form.get("password"):
            return Response(400, SIGNUP.replace("<form", "<p>Choose another name</p><form"))
        users[name] = {"password": form["password"], "email": form.get("email", "")}
        return Response(302, "", {"Location": "/login"})

    def login(request: Request) -> Response:
        form = request.form()
        name = str(form.get("username") or "")
        for candidate, record in users.items():
            if name in (candidate, record["email"]) and form.get("password") == record["password"]:
                token = "zoo-" + secrets.token_hex(8)
                sessions[token] = candidate
                return Response(302, "", {"Location": "/tasks", "Set-Cookie": "sid=%s; Path=/; HttpOnly" % token})
        return Response(200, LOGIN.replace("<form", "<p>Invalid username or password</p><form"))

    def listing(request: Request) -> Response:
        user = user_of(request)
        if not user:
            return Response(302, "", {"Location": "/login"})
        items = ""
        for task_id, task in tasks.items():
            if task["owner"] == user:
                items += '<li><a href="/tasks/%s">%s</a></li>' % (task_id, task["title"])
        return Response(200, "<html><body><h1>%s's tasks</h1><ul>%s</ul><a href='/logout'>Sign out</a>"
                             "</body></html>" % (user, items))

    def task(request: Request) -> Response:
        user = user_of(request)
        if not user:
            return Response(302, "", {"Location": "/login"})
        item = tasks.get(request.path.rsplit("/", 1)[-1])
        if item is None or (safe and item["owner"] != user):
            return Response(404, "<html><body>No such task</body></html>")
        return Response(200, "<html><body><h1>%s</h1><p>%s</p><p>owner: %s</p></body></html>"
                             % (item["title"], item["note"], item["owner"]))

    app.route("GET", "/register", lambda request: Response(200, SIGNUP))
    app.route("POST", "/register", register)
    app.route("GET", "/login", lambda request: Response(200, LOGIN))
    app.route("POST", "/login", login)
    app.route("GET", "/tasks", listing)
    app.route("GET", "/tasks/*", task)
    return app
