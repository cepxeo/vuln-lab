"""Generic vulnerable apps for the zoo, each with a safe twin.

``build(safe, variant)`` returns an App. The variants are the conditions that
broke in live scans:
- "catch-all": every unknown path answers one constant 200 body (a proxy edge);
- "large-body": the interesting part sits after 64 KB of page;
- "json": the same sink behind a JSON API instead of a form or query;
- "filter-403": the app's input filter answers 403 instead of 400;
- "cookie": the session token travels in a cookie, not a Bearer header;
- "login-elsewhere": the login form lives on one page and posts to another;
- "no-session": the sink is public, the engagement has no session;
- "patch-only": the write route takes PATCH only.

Nothing here copies a lab app: the shapes are the common ones.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import posixpath
import re
import urllib.request
from urllib.parse import unquote, urlsplit

from authorization_tests.vulnzoo.server import App, Request, Response, Route, json_response, segment

PASSWD = "root:x:0:0:root:/root:/bin/bash\ndaemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
PADDING = "<p>" + ("lorem ipsum dolor sit amet " * 2600) + "</p>"  # about 70 KB
CATCH_ALL_BODY = "<html><body>edge</body></html>"
APACHE_403 = ("<!DOCTYPE HTML><html><head><title>403 Forbidden</title></head><body><h1>Forbidden</h1><p>You "
              "don't have permission to access this resource.</p><hr><address>Apache Server at app Port 80"
              "</address></body></html>")


def _catch_all(_request: Request) -> Response:
    return Response(200, CATCH_ALL_BODY)


def _home(title: str, links=(), extra: str = ""):
    anchors = "".join('<a href="%s">%s</a> ' % (link, link) for link in links)
    page = "<html><head><title>%s</title></head><body><h1>%s</h1>%s%s</body></html>" % (title, title, anchors, extra)

    def handler(_request: Request) -> Response:
        return Response(200, page)

    return handler


def _base(variant: str, title: str = "Inventory", links=()) -> App:
    app = App()
    app.route("GET", "/", _home(title, links, PADDING if variant == "large-body" else ""))
    if variant == "catch-all":
        app.fallback = _catch_all
    return app


# -- CORS -------------------------------------------------------------------------


def cors(safe: bool, variant: str) -> App:
    app = _base(variant)

    def api(request: Request) -> Response:
        origin = request.headers.get("origin", "")
        headers = {}
        if origin and not safe:
            headers = {"Access-Control-Allow-Origin": origin, "Access-Control-Allow-Credentials": "true"}
        elif origin:
            headers = {"Access-Control-Allow-Origin": "https://portal.corp.example",
                       "Access-Control-Allow-Credentials": "true"}
        if variant == "json":
            return json_response({"items": [1, 2]}, headers=headers)
        body = "<html><body>account</body></html>" + (PADDING if variant == "large-body" else "")
        return Response(200, body, headers)

    app.routes.insert(0, Route("GET", "/", api))
    return app


# -- server exposure ---------------------------------------------------------------


def status_page(safe: bool, variant: str) -> App:
    app = _base(variant)
    if safe:
        app.route("GET", "/server-status", lambda request: Response(403, APACHE_403))
    else:
        app.route("GET", "/server-status", lambda request: Response(
            200, "<html><body><h1>Apache Server Status for app</h1><dl><dt>Server uptime: 3 days</dt>"
                 "<dt>Total accesses: 1200</dt></dl><pre>Scoreboard: __W__K__</pre></body></html>"))
    return app


def directory_listing(safe: bool, variant: str) -> App:
    app = _base(variant, links=("/assets/js/app.js",))
    app.route("GET", "/assets/js/app.js", lambda request: Response(200, "console.log(1)",
                                                                  content_type="application/javascript"))
    if safe:
        app.route("GET", "/assets/", lambda request: Response(403, APACHE_403))
    else:
        app.route("GET", "/assets/", lambda request: Response(
            200, "<html><head><title>Index of /assets/</title></head><body><h1>Index of /assets/</h1><pre>"
                 '<a href="../">../</a>\n<a href="js/">js/</a>\n<a href="backup.zip">backup.zip</a></pre></body></html>'))
    return app


def version_banner(safe: bool, variant: str) -> App:
    app = _base(variant)
    app.headers["Server"] = "nginx" if safe else "nginx/1.25.5"
    return app


# -- path traversal ------------------------------------------------------------------


def file_segment(safe: bool, variant: str) -> App:
    """/files/<name>: the router decodes the segment once, a guard rejects "..",
    and the vulnerable app decodes the name again before opening it."""
    app = _base(variant, links=("/files/readme.txt",))

    def serve(request: Request) -> Response:
        name = segment(request, "/files/")
        if "/" in request.path[len("/files/"):]:
            return Response(404, "not found")
        if ".." in name:
            return Response(403 if variant == "filter-403" else 400, "bad file name")
        if not safe:
            name = unquote(name)
        resolved = posixpath.normpath(posixpath.join("/srv/files", name))
        if resolved == "/etc/passwd":
            return Response(200, PASSWD, content_type="text/plain")
        if resolved == "/srv/files/readme.txt":
            return Response(200, "release notes", content_type="text/plain")
        return Response(404, "no such file")

    app.route("GET", "/files/*", serve)
    return app


def query_file(safe: bool, variant: str) -> App:
    """/download?file=<name> reads a file under a base directory."""
    app = _base(variant, links=("/download?file=report.pdf",))

    def serve(request: Request) -> Response:
        name = request.arg("file") or request.arg("path")
        if safe and (".." in name or name.startswith("/")):
            return Response(400, "invalid name")
        resolved = posixpath.normpath(posixpath.join("/srv/reports", name.replace("....//", "../")))
        if resolved == "/etc/passwd":
            return Response(200, PASSWD, content_type="text/plain")
        return Response(200, "%PDF-1.4 report" if name == "report.pdf" else "not found",
                        content_type="application/octet-stream")

    app.route("GET", "/download", serve)
    return app


def alias_edge(safe: bool, variant: str) -> App:
    """A catch-all edge with /static/ aliased to a directory; the vulnerable
    location lacks the trailing slash, so /static../ reaches the parent."""
    app = App(fallback=_catch_all)
    app.route("GET", "/", _home("edge"))
    listing = ("<html><head><title>Index of /static/</title></head><body><h1>Index of /static/</h1><pre>"
               '<a href="app.css">app.css</a></pre></body></html>')
    parent = ("<html><head><title>Index of /</title></head><body><h1>Index of /</h1><pre>"
              '<a href="static/">static/</a>\n<a href="config/">config/</a></pre></body></html>')
    app.route("GET", "/static/", lambda request: Response(200, listing))

    def dotdot(request: Request) -> Response:
        if safe:
            return _catch_all(request)
        return Response(200, parent)

    app.route("GET", "/static../*", dotdot)
    app.route("GET", "/static..%2f*", dotdot)
    return app


# -- JWT ---------------------------------------------------------------------------------


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def sign_hs256(claims: dict, secret: str) -> str:
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()) + "." + _b64(json.dumps(claims).encode())
    return head + "." + _b64(hmac.new(secret.encode(), head.encode(), hashlib.sha256).digest())


def _verify(token: str, secret: str, accept_none: bool):
    parts = str(token or "").split(".")
    if len(parts) != 3:
        return None
    try:
        header = json.loads(_unb64(parts[0]))
        claims = json.loads(_unb64(parts[1]))
    except (ValueError, TypeError):
        return None
    if header.get("alg") == "none":
        return claims if accept_none and not parts[2] else None
    expected = _b64(hmac.new(secret.encode(), (parts[0] + "." + parts[1]).encode(), hashlib.sha256).digest())
    return claims if hmac.compare_digest(expected, parts[2]) else None


JWT_SECRET = "a-long-random-server-secret-1f6c2e9b"
JWT_USER_TOKEN = sign_hs256({"sub": "7", "name": "member", "role": "user"}, JWT_SECRET)


def jwt_alg_none(safe: bool, variant: str) -> App:
    """/api/me needs a JWT (Bearer, or the "session" cookie in the cookie variant);
    the vulnerable verifier also takes alg=none."""
    app = _base(variant)

    def me(request: Request) -> Response:
        token = request.cookie("session") if variant == "cookie" else request.bearer()
        claims = _verify(token, JWT_SECRET, accept_none=not safe)
        if claims is None:
            return json_response({"error": "authentication required"}, 401)
        return json_response({"id": claims.get("sub"), "name": claims.get("name"), "plan": "gold"})

    app.route("GET", "/api/me", me)
    return app


def jwt_weak_secret(safe: bool, variant: str) -> App:
    """No login works; the token secret is the app's name in a common form."""
    secret = "a-long-random-server-secret-77d1" if safe else "quillpad-dev-secret"
    app = _base(variant, title="Quillpad")

    def me(request: Request) -> Response:
        # "cookie": the token travels in the "auth" cookie and a bad token is
        # answered unlike a missing one; "cookie-same-error": the same, but both
        # get the same answer (no hint which channel the app reads).
        token = request.bearer() if not variant.startswith("cookie") else request.cookie("auth")
        claims = _verify(token, secret, accept_none=False)
        if claims is None:
            message = "invalid token" if token and variant == "cookie" else "authentication required"
            return json_response({"error": message}, 401)
        return json_response({"user": claims.get("sub"), "notes": 3})

    app.route("GET", "/api/me", me)
    return app


# -- JSON API with a session: prototype pollution, mass assignment ------------------------------


class _Node:
    def __init__(self):
        self.principal = {"id": 7, "email": "member@corp.example", "role": "member"}
        self.proto = {}


def _node_json(node: _Node, data) -> str:
    spaces = int(node.proto.get("json spaces") or 0)
    return json.dumps(data, indent=spaces) if spaces else json.dumps(data, separators=(",", ":"))


def _merge(node: _Node, data, safe: bool) -> None:
    if not isinstance(data, dict) or safe:
        return
    # A recursive merge that walks constructor.prototype onto Object.prototype.
    proto = ((data.get("constructor") or {}).get("prototype") or {}) if isinstance(data.get("constructor"), dict) else {}
    under = data.get("__proto__") if isinstance(data.get("__proto__"), dict) else {}
    for source in (proto, under):
        for key, value in source.items():
            node.proto[key] = value


def prototype_gadget(safe: bool, variant: str) -> App:
    node = _Node()
    app = _base(variant)
    app.route("GET", "/api/me", lambda request: Response(200, _node_json(node, node.principal),
                                                         content_type="application/json"))
    method = "PATCH" if variant == "patch-only" else "POST"

    def settings(request: Request) -> Response:
        _merge(node, request.json(), safe)
        return Response(200, _node_json(node, {"ok": True}), content_type="application/json")

    app.route(method, "/api/settings", settings)
    app.route("GET", "/api/settings", lambda request: Response(200, _node_json(node, {"theme": "light"}),
                                                               content_type="application/json"))
    app.node = node
    return app


def mass_assignment(safe: bool, variant: str) -> App:
    node = _Node()
    if variant == "rescan":
        # An earlier scan left its fixed marker behind (refactor plan 2, B12).
        node.principal["role"] = "scansuite_ma_role"
    app = _base(variant)

    def principal(_request: Request) -> Response:
        # "large-body": a long activity list comes before the fields, so a
        # changed role sits after the first 64 KB of the answer.
        if variant == "large-body":
            data = {"activity": ["login from 10.0.%d.%d" % (i // 250, i % 250) for i in range(4000)]}
            data.update(node.principal)
            return json_response(data)
        return json_response(node.principal)

    app.route("GET", "/api/me", principal)
    app.route("GET", "/api/profile", principal)

    def update(request: Request) -> Response:
        data = request.json() or {}
        for key, value in data.items() if isinstance(data, dict) else ():
            if key in ("email", "display_name") or (not safe and key in ("role", "owner", "is_admin")):
                node.principal[key] = value
        return json_response({"updated": True})

    app.route("PUT", "/api/profile", update)
    app.node = node
    return app


# -- SSRF --------------------------------------------------------------------------------------


def _fetch_loopback(url: str) -> bool:
    """Fetch ``url`` when it points at the loopback (the zoo's collector), as a
    server-side fetcher would; nothing else is ever reached."""
    host = urlsplit(url).hostname or ""
    if host != "127.0.0.1":
        return False
    try:
        with urllib.request.urlopen(url, timeout=3) as reply:  # noqa: S310 - loopback only
            reply.read(64)
    except Exception:  # noqa: BLE001 - a failed fetch is still a fetch attempt
        return False
    return True


def ssrf_fetch(safe: bool, variant: str) -> App:
    """/media/preview?url=<image URL> fetches the URL server-side. The safe twin
    allows only its CDN host, compared exactly."""
    app = _base(variant, links=("/media/preview?url=http://cdn.corp.example/logo.png",))

    def preview(request: Request) -> Response:
        target = str(request.args().get("url") or "")
        host = urlsplit(target).hostname or ""
        if safe and host != "cdn.corp.example":
            return Response(400, "host not allowed")
        _fetch_loopback(target)
        return Response(200, "<img src='data:,'>")

    if variant == "json":
        app.route("POST", "/api/import", preview)
    else:
        app.route("GET", "/media/preview", preview)
    return app


# -- SSTI ------------------------------------------------------------------------------------------


def ssti(safe: bool, variant: str) -> App:
    app = _base(variant, links=("/greet?name=guest",))

    def greet(request: Request) -> Response:
        name = request.arg("name")
        if not safe:
            name = re.sub(r"\{\{\s*(\d+)\s*\*\s*(\d+)\s*\}\}", lambda m: str(int(m.group(1)) * int(m.group(2))), name)
        escaped = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        return Response(200, "<html><body><p>Hello " + escaped + "</p></body></html>")

    app.route("GET", "/greet", greet)
    return app


# -- default credentials -------------------------------------------------------------------------------


LOGIN_FORM = ('<html><body><form method="post" action="{action}"><input name="username">'
              '<input type="password" name="password"><button>Sign in</button></form></body></html>')


def default_credentials(safe: bool, variant: str) -> App:
    """A form login; the vulnerable app still takes admin/admin. In the
    login-elsewhere variant the form lives on /login and posts to /session."""
    app = _base(variant, links=("/login",))
    action = "/session" if variant == "login-elsewhere" else "/login"
    # "csrf-token": every form carries a single-use token the POST must return.
    issued: set = set()

    def form_page(_request: Request) -> Response:
        page = LOGIN_FORM.format(action=action)
        if variant == "csrf-token":
            import secrets

            token = secrets.token_hex(8)
            issued.add(token)
            page = page.replace("<input name=\"username\">",
                                '<input type="hidden" name="csrf_token" value="%s"><input name="username">' % token)
        return Response(200, page)

    app.route("GET", "/login", form_page)

    def submit(request: Request) -> Response:
        form = request.form()
        if variant == "csrf-token":
            token = form.get("csrf_token", "")
            if token not in issued:
                return Response(403, "<p>invalid CSRF token</p>")
            issued.discard(token)
        good = not safe and form.get("username") == "admin" and form.get("password") == "admin"
        if good:
            return Response(302, "", {"Location": "/dashboard", "Set-Cookie": "sid=zoo-session-1; Path=/; HttpOnly"})
        return Response(200, LOGIN_FORM.format(action=action).replace("<form", "<p>Invalid username or password</p><form"))

    app.route("POST", action, submit)

    def dashboard(request: Request) -> Response:
        if request.cookie("sid") != "zoo-session-1":
            return Response(302, "", {"Location": "/login"})
        return Response(200, "<html><body><h1>Dashboard</h1><a href='/logout'>Sign out</a> admin</body></html>")

    app.route("GET", "/dashboard", dashboard)
    return app
