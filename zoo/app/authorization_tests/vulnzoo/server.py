"""A stdlib fixture server for the zoo: loopback only, port 0, one app per server.

An app is a list of routes (method, path or path prefix, handler) plus a
fallback. A handler takes a Request and returns a Response. Nothing here
reaches beyond 127.0.0.1.
"""
from __future__ import annotations

import json
import socket
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qsl, unquote, urlsplit


@dataclass
class Request:
    method: str
    raw_path: str  # the request-target as sent, percent-escapes kept
    path: str  # raw_path without the query, still percent-encoded
    query: list  # (name, value) pairs, decoded once
    headers: dict  # lower-case name -> value
    body: bytes = b""

    @property
    def text(self) -> str:
        return self.body.decode("utf-8", "replace")

    def json(self):
        try:
            return json.loads(self.text or "null")
        except ValueError:
            return None

    def form(self) -> dict:
        return dict(parse_qsl(self.text, keep_blank_values=True))

    def arg(self, name: str, default: str = "") -> str:
        for key, value in self.query:
            if key == name:
                return value
        return default

    def args(self) -> dict:
        """Query, then form or JSON body fields, first value wins."""
        out: dict = {}
        for key, value in self.query:
            out.setdefault(key, value)
        content_type = self.headers.get("content-type", "")
        if "json" in content_type:
            data = self.json()
            if isinstance(data, dict):
                for key, value in data.items():
                    out.setdefault(str(key), value)
        elif self.body:
            for key, value in self.form().items():
                out.setdefault(key, value)
        return out

    def cookie(self, name: str) -> str:
        for part in self.headers.get("cookie", "").split(";"):
            key, _, value = part.strip().partition("=")
            if key == name:
                return value
        return ""

    def bearer(self) -> str:
        auth = self.headers.get("authorization", "")
        return auth[7:] if auth.startswith("Bearer ") else ""


@dataclass
class Response:
    status: int = 200
    body: str | bytes = ""
    headers: dict = field(default_factory=dict)
    content_type: str = "text/html; charset=utf-8"

    def payload(self) -> bytes:
        return self.body if isinstance(self.body, bytes) else str(self.body).encode("utf-8")


def json_response(data, status: int = 200, headers: dict | None = None, indent=None) -> Response:
    return Response(status, json.dumps(data, indent=indent), dict(headers or {}), "application/json")


Handler = Callable[[Request], Response]


@dataclass
class Route:
    method: str  # "*" for any
    path: str  # exact path, or a prefix when it ends with "*"
    handler: Handler

    def matches_path(self, path: str) -> bool:
        if self.path.endswith("*"):
            return path.startswith(self.path[:-1])
        return path == self.path

    def matches(self, method: str, path: str) -> bool:
        if self.method != "*" and self.method != method:
            return False
        return self.matches_path(path)


def not_found(_request: Request) -> Response:
    return Response(404, "not found", content_type="text/plain")


@dataclass
class App:
    routes: list = field(default_factory=list)
    fallback: Handler = not_found
    # Headers added to every answer (a Server banner, a CORS policy).
    headers: dict = field(default_factory=dict)
    # Called with every request before routing; may answer itself (a filter).
    before: Callable[[Request], Response | None] | None = None

    def route(self, method: str, path: str, handler: Handler) -> "App":
        self.routes.append(Route(method, path, handler))
        return self

    def dispatch(self, request: Request) -> Response:
        if self.before is not None:
            early = self.before(request)
            if early is not None:
                return early
        for route in self.routes:
            if route.matches(request.method, request.path):
                return route.handler(request)
        for route in self.routes:
            if route.matches_path(request.path):
                # The path exists for another method, as a framework answers.
                return Response(405, "method not allowed", content_type="text/plain")
        return self.fallback(request)


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "zoo"
    sys_version = ""

    def setup(self):
        super().setup()
        # Headers and body go out in two writes; without this, Nagle and the
        # client's delayed ACK add 40 ms to every keep-alive answer.
        self.connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def _serve(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        parts = urlsplit(self.path)
        query = parse_qsl(parts.query, keep_blank_values=True)
        headers = {}
        for key, value in self.headers.items():
            headers[key.lower()] = value
        request = Request(self.command, self.path, parts.path, query, headers, body)
        self.server.requests.append(request)
        try:
            response = self.server.app.dispatch(request)
        except Exception as exc:  # noqa: BLE001 - a broken case answers 500, like an app would
            response = Response(500, "zoo handler error: " + type(exc).__name__, content_type="text/plain")
        payload = response.payload()
        self.send_response(response.status)
        sent = set()
        for key, value in list(self.server.app.headers.items()) + list(response.headers.items()):
            self.send_header(key, value)
            sent.add(key.lower())
        if "content-type" not in sent:
            self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(payload)

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = _serve

    def log_message(self, *args):
        pass


class _QuietServer(ThreadingHTTPServer):
    """A scanner closes connections mid-answer all the time (dalfox, nuclei); that
    is no error of the app, so no traceback for it."""

    def handle_error(self, request, client_address):
        import sys

        if isinstance(sys.exc_info()[1], ConnectionError):
            return
        super().handle_error(request, client_address)


class ZooServer:
    """``with ZooServer(app) as server: server.base`` -> http://127.0.0.1:<port>. Loopback and an
    ephemeral port unless the live smoke run (serve.py) asks for another."""

    def __init__(self, app: App, bind: str = "127.0.0.1", port: int = 0) -> None:
        self.bind = bind
        self.port = port
        self.app = app
        self.httpd = None
        self.thread = None

    def __enter__(self) -> "ZooServer":
        self.httpd = _QuietServer((self.bind, self.port), _Handler)
        self.httpd.daemon_threads = True
        self.httpd.app = self.app
        self.httpd.requests = []
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.02}, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *exc) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def base(self) -> str:
        return f"http://127.0.0.1:{self.httpd.server_address[1]}"

    @property
    def requests(self) -> list:
        return self.httpd.requests


def segment(request: Request, prefix: str) -> str:
    """The path after ``prefix``, decoded once, as a router hands a path parameter."""
    return unquote(request.path[len(prefix):])


# The collectors running now: a zoo app's name lookup reaches them (resolve_name).
_ACTIVE_COLLECTORS: list = []


def resolve_name(name: str) -> bool:
    """A zoo app "looks up" a host name: a running collector whose DNS domain it is
    in records the DNS interaction, as a real collector's DNS server would. True
    when one did. Nothing leaves the process."""
    for collector in list(_ACTIVE_COLLECTORS):
        if collector.record_dns(name):
            return True
    return False


class Collector:
    """An in-process out-of-band collector with the real collector's HTTP API
    (GET /info, GET /interactions/<id>, both with X-Collector-Key) and a callback
    endpoint on the same port: any request whose path starts with a listener id
    is an interaction. The engine's real OobClient talks to it."""

    KEY = "zoo-collector-key"
    DNS_DOMAIN = "oob.zoo.test"

    def __init__(self) -> None:
        self.interactions: dict = {}
        self.server = None

    def _app(self) -> App:
        app = App()
        app.route("GET", "/info", self._info)
        app.route("GET", "/interactions/*", self._list)
        app.fallback = self._callback
        return app

    def _info(self, request: Request) -> Response:
        if request.headers.get("x-collector-key") != self.KEY:
            return Response(401, "key")
        port = self.server.httpd.server_address[1]
        return json_response({"public_host": "127.0.0.1", "http_port": port, "dns_domain": self.DNS_DOMAIN})

    def _list(self, request: Request) -> Response:
        if request.headers.get("x-collector-key") != self.KEY:
            return Response(401, "key")
        listener_id = request.path.rsplit("/", 1)[-1]
        return json_response({"interactions": list(self.interactions.get(listener_id, []))})

    def _callback(self, request: Request) -> Response:
        listener_id = request.path.strip("/").split("/", 1)[0]
        self.interactions.setdefault(listener_id, []).append(
            {"protocol": "http", "method": request.method, "path": request.path, "remote": "127.0.0.1",
             "headers": {"User-Agent": request.headers.get("user-agent", "")}})
        return Response(200, "ok", content_type="text/plain")

    def record_dns(self, name: str) -> bool:
        """A lookup of <listener id>.<domain>: the listener's DNS interaction."""
        name = str(name or "").lower().rstrip(".")
        suffix = "." + self.DNS_DOMAIN
        if not name.endswith(suffix):
            return False
        listener_id = name[:-len(suffix)].split(".")[-1]
        self.interactions.setdefault(listener_id, []).append(
            {"protocol": "dns", "qname": name, "remote": "127.0.0.1"})
        return True

    def __enter__(self) -> "Collector":
        self.server = ZooServer(self._app()).__enter__()
        _ACTIVE_COLLECTORS.append(self)
        return self

    def __exit__(self, *exc) -> None:
        if self in _ACTIVE_COLLECTORS:
            _ACTIVE_COLLECTORS.remove(self)
        self.server.__exit__(*exc)

    @property
    def url(self) -> str:
        return self.server.base

    def hits(self) -> int:
        total = 0
        for items in self.interactions.values():
            total += len(items)
        return total
