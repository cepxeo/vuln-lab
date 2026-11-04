"""DAST sinks for the zoo: one parameter each, driven by the DAST checks with a
scripted payload decision in place of the model. Each has a safe twin.

The sinks behave like the real thing where the standard library allows it (a
real SQLite query built by concatenation); a shell, a file system and outbound
fetches are emulated without leaving the process.
"""
from __future__ import annotations

import posixpath
import re
import sqlite3
from urllib.parse import urlsplit

from authorization_tests.vulnzoo.apps import PADDING, PASSWD, _base, cors, default_credentials
from authorization_tests.vulnzoo.server import App, Request, Response, json_response


def _escape(text) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _page(body: str, variant: str) -> str:
    padding = PADDING if variant == "large-body" else ""
    return "<html><body>" + padding + body + "</body></html>"


def sqli(safe: bool, variant: str) -> App:
    """/products?q= over a real SQLite table, the query built by concatenation.
    "base" shows the database error; "blind" hides it (rows or none only)."""
    db = sqlite3.connect(":memory:", check_same_thread=False)
    db.execute("CREATE TABLE products (name TEXT, price INTEGER)")
    db.executemany("INSERT INTO products VALUES (?, ?)", [("lamp", 30), ("desk", 120), ("chair", 80)])
    app = _base(variant, links=("/products?q=lamp",))

    def products(request: Request) -> Response:
        term = str(request.args().get("q") or "")
        try:
            if safe:
                rows = db.execute("SELECT name, price FROM products WHERE name LIKE ?", ("%" + term + "%",)).fetchall()
            else:
                rows = db.execute("SELECT name, price FROM products WHERE name LIKE '%" + term + "%'").fetchall()
        except sqlite3.Error as exc:
            if variant == "blind":
                rows = []
            else:
                return Response(500, _page("<pre>sqlite3.OperationalError: %s</pre>" % _escape(exc), variant))
        items = ""
        for name, price in rows:
            items += "<li>%s %d</li>" % (_escape(name), price)
        return Response(200, _page("<ul>%s</ul><p>%d results</p>" % (items, len(rows)), variant))

    app.route("GET", "/products", products)
    return app


def reflected_xss(safe: bool, variant: str) -> App:
    app = _base(variant, links=("/search?q=lamp",))

    def search(request: Request) -> Response:
        term = request.arg("q")
        shown = _escape(term) if safe else term
        return Response(200, _page("<p>Results for " + shown + "</p>", variant))

    app.route("GET", "/search", search)
    return app


def stored_xss(safe: bool, variant: str) -> App:
    comments: list = []
    app = _base(variant)

    def board(_request: Request) -> Response:
        items = ""
        for text in comments:
            items += "<li>%s</li>" % (_escape(text) if safe else text)
        form = '<form method="post" action="/comments"><textarea name="body"></textarea><button>Post</button></form>'
        return Response(200, _page("<ul>%s</ul>%s" % (items, form), variant))

    def post(request: Request) -> Response:
        comments.append(str(request.form().get("body") or ""))
        return Response(302, "", {"Location": "/comments"})

    app.route("GET", "/comments", board)
    app.route("POST", "/comments", post)
    return app


def _shell_emulation(host: str) -> list:
    """What `ping -c 1 <host>` through a shell would print, emulated without a
    shell: a metacharacter starts a second command; `id`, `echo` and `$((a*b))`
    are understood."""
    first = re.split(r";|\||`|\$\(|&&", host, maxsplit=1)[0]
    lines = ["PING %s: 56 data bytes" % first]
    injected = re.search(r"(;|\|\||\||&&|`|\$\()", host)
    if not injected:
        return lines
    tail = host[injected.start():]
    for match in re.finditer(r"echo\s+([A-Za-z0-9_]*)\$\(\((\d+)\s*\*\s*(\d+)\)\)", tail):
        lines.append(match.group(1) + str(int(match.group(2)) * int(match.group(3))))
    if re.search(r"(?:;|\||`|\$\()\s*id\b", tail):
        lines.append("uid=33(www-data) gid=33(www-data) groups=33(www-data)")
    return lines


def command_injection(safe: bool, variant: str) -> App:
    app = _base(variant, links=("/tools/ping?host=127.0.0.1",))

    def ping(request: Request) -> Response:
        host = str(request.args().get("host") or "")
        if safe and not re.fullmatch(r"[A-Za-z0-9.\-]{1,253}", host):
            return Response(400, _page("<p>invalid host</p>", variant))
        lines = ["PING %s: 56 data bytes" % host] if safe else _shell_emulation(host)
        return Response(200, _page("<pre>" + _escape("\n".join(lines)) + "</pre>", variant))

    app.route("GET", "/tools/ping", ping)
    return app


def _evaluate_template(text: str) -> str:
    def product(match):
        return str(int(match.group(1)) * int(match.group(2)))

    text = re.sub(r"\{\{\s*(\d+)\s*\*\s*(\d+)\s*\}\}", product, text)
    return re.sub(r"\$\{\s*(\d+)\s*\*\s*(\d+)\s*\}", product, text)


def ssti(safe: bool, variant: str) -> App:
    app = _base(variant, links=("/hello?name=guest",))

    def hello(request: Request) -> Response:
        name = request.arg("name")
        rendered = _escape(name) if safe else _escape(_evaluate_template(name))
        return Response(200, _page("<p>Hello " + rendered + "</p>", variant))

    app.route("GET", "/hello", hello)
    return app


def ssrf(safe: bool, variant: str) -> App:
    """/fetch?url=: the server fetches the URL and shows it. Emulated without
    leaving the process: file:// and loopback answer locally, nothing else does."""
    app = _base(variant, links=("/fetch?url=https://cdn.corp.example/a.png",))

    def fetch(request: Request) -> Response:
        target = request.arg("url")
        parts = urlsplit(target)
        if safe and not (parts.scheme == "https" and parts.hostname == "cdn.corp.example"):
            return Response(400, _page("<p>url not allowed</p>", variant))
        if parts.scheme == "file" and parts.path.endswith("/etc/passwd"):
            return Response(200, _page("<pre>" + PASSWD + "</pre>", variant))
        if parts.hostname in ("127.0.0.1", "localhost"):
            return Response(200, _page("<h1>Internal admin console</h1><p>build 4.2, node intranet-7</p>", variant))
        if parts.hostname == "169.254.169.254":
            return Response(200, _page('<pre>{"instance-id": "i-0abc", "iam": {"role": "app"}}</pre>', variant))
        return Response(200, _page("<img alt='preview'>", variant))

    app.route("GET", "/fetch", fetch)
    return app


def open_redirect(safe: bool, variant: str) -> App:
    app = _base(variant, links=("/go?next=/account",))

    def go(request: Request) -> Response:
        target = request.arg("next") or "/"
        if safe and (not target.startswith("/") or target.startswith("//")):
            target = "/"
        return Response(302, "", {"Location": target})

    app.route("GET", "/go", go)
    app.route("GET", "/account", lambda request: Response(200, _page("<p>account</p>", variant)))
    return app


def path_traversal(safe: bool, variant: str) -> App:
    app = _base(variant, links=("/view?file=intro.txt",))

    def view(request: Request) -> Response:
        name = request.arg("file")
        if safe and (".." in name or name.startswith("/")):
            return Response(400, _page("<p>invalid file</p>", variant))
        resolved = posixpath.normpath(posixpath.join("/srv/docs", name))
        if resolved == "/etc/passwd":
            return Response(200, _page("<pre>" + PASSWD + "</pre>", variant))
        found = resolved == "/srv/docs/intro.txt"
        return Response(200, _page("<pre>intro text</pre>" if found else "<p>missing</p>", variant))

    app.route("GET", "/view", view)
    return app


def xxe(safe: bool, variant: str) -> App:
    """POST /api/orders takes XML. The vulnerable parser resolves an external
    file entity (emulated: only file:///etc/passwd exists); the safe one refuses
    a DOCTYPE."""
    app = _base(variant)

    def orders(request: Request) -> Response:
        text = request.text
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            if safe:
                return Response(400, "<error>DTD is not allowed</error>", content_type="application/xml")
            for name, system_id in re.findall(r'<!ENTITY\s+(\w+)\s+SYSTEM\s+"([^"]+)"', text):
                text = text.replace("&%s;" % name, PASSWD if system_id.endswith("/etc/passwd") else "")
        item = re.search(r"<item>(.*?)</item>", text, re.S)
        shown = item.group(1) if item else ""
        return Response(200, "<order><accepted>" + _escape(shown) + "</accepted></order>",
                        content_type="application/xml")

    app.route("POST", "/api/orders", orders)
    return app


def dast_cors(safe: bool, variant: str) -> App:
    return cors(safe, variant)


def clickjacking(safe: bool, variant: str) -> App:
    app = _base(variant)
    headers = {"X-Frame-Options": "DENY", "Content-Security-Policy": "frame-ancestors 'none'"} if safe else {}

    def settings(_request: Request) -> Response:
        return Response(200, _page("<form><input name='email'></form>", variant), dict(headers))

    app.route("GET", "/account/settings", settings)
    return app


def info_disclosure(safe: bool, variant: str) -> App:
    """/report?format=: an unknown format raises; the vulnerable app answers with
    the traceback and its settings, the safe one with a generic error."""
    app = _base(variant)

    def report(request: Request) -> Response:
        fmt = request.arg("format") or "pdf"
        if fmt in ("pdf", "csv"):
            return Response(200, _page("<p>report ready</p>", variant))
        if safe:
            return Response(400, _page("<p>unsupported format</p>", variant))
        trace = ("Traceback (most recent call last):\n  File \"/srv/app/reports.py\", line 88, in render\n"
                 "    exporter = EXPORTERS[fmt]\nKeyError: '%s'\n\nSettings: DATABASE_URL=postgres://app:"
                 "zoo-db-pass@db.internal:5432/app  SECRET_KEY=8f2b1c9d0e7a6f5b4c3d2e1f0a9b8c7d") % fmt
        return Response(500, _page("<pre>" + _escape(trace) + "</pre>", variant))

    app.route("GET", "/report", report)
    return app


USERS = (
    {"name": "alice", "role": "member", "email": "alice@corp.example", "plan": "gold"},
    {"name": "bob", "role": "member", "email": "bob@corp.example", "plan": "free"},
    {"name": "carol", "role": "admin", "email": "carol@corp.example", "plan": "gold"},
    {"name": "dave", "role": "member", "email": "dave@corp.example", "plan": "trial"},
)


def nosql(safe: bool, variant: str) -> App:
    """/api/users?name=<name>: the name goes into a document-store query. The
    vulnerable app JSON-decodes a value that looks like an object and passes it
    on as the query value, so {"$ne": ...} is an operator (it matches every
    user); the safe one treats every value as a plain string."""
    app = _base(variant, links=("/api/users?name=alice",))

    def matches(stored, given) -> bool:
        if isinstance(given, dict):
            if "$ne" in given:
                return stored != given["$ne"]
            if "$gt" in given:
                return str(stored) > str(given["$gt"])
            if "$regex" in given:
                return re.search(str(given["$regex"]), str(stored)) is not None
            return False
        return stored == given

    def users(request: Request) -> Response:
        import json

        raw = request.arg("name")
        given = raw
        if not safe and raw.strip().startswith("{"):
            try:
                given = json.loads(raw)
            except ValueError:
                given = raw
        found = []
        for user in USERS:
            if matches(user["name"], given):
                found.append(user)
        return json_response({"users": found, "count": len(found)})

    app.route("GET", "/api/users", users)
    return app


def weak_credentials(safe: bool, variant: str) -> App:
    return default_credentials(safe, variant)
