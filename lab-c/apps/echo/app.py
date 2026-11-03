"""Echo API: a false-positive trap for the AI pentest benchmark (weak-sides plan 0.1.5).

Every endpoint reflects what it is sent -- the request body, the query, the bad
value in a validation error -- but always safely: JSON with a JSON content type,
HTML escaped, no database, no shell, no file access, no outbound requests. A
scanner that reports injection, XSS, SQL errors or verbose errors here has
mistaken reflection for a vulnerability. Ground truth: no findings.

Standard library only (no dependencies to pin or patch).
"""
import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

PORT = 5007
ITEMS = {1: "tomato", 2: "basil", 3: "olive oil"}
INDEX = """<!doctype html><html><head><title>Echo API</title></head><body>
<h1>Echo API</h1><p>You asked for: {path}</p>
<ul><li>GET /search?q=...</li><li>POST /api/echo (JSON)</li><li>POST /api/validate (JSON)</li>
<li>GET /api/items/&lt;id&gt;</li></ul></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "echo"
    sys_version = ""

    def _send(self, status, body, content_type):
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _json(self, status, payload):
        self._send(status, json.dumps(payload), "application/json; charset=utf-8")

    def _body(self):
        length = min(int(self.headers.get("Content-Length") or 0), 64 * 1024)
        raw = self.rfile.read(length) if length else b""
        try:
            return json.loads(raw.decode("utf-8") or "{}"), None
        except (UnicodeDecodeError, ValueError) as exc:
            return None, "invalid JSON: " + str(exc)

    def do_GET(self):
        parts = urlsplit(self.path)
        query = parse_qs(parts.query)
        if parts.path == "/":
            self._send(200, INDEX.format(path=html.escape(self.path)), "text/html; charset=utf-8")
        elif parts.path == "/search":
            term = (query.get("q") or [""])[0]
            self._json(200, {"query": term, "results": [name for name in ITEMS.values() if term.lower() in name]})
        elif parts.path.startswith("/api/items/"):
            raw = parts.path[len("/api/items/"):]
            if not re.fullmatch(r"\d{1,6}", raw):
                self._json(400, {"error": "invalid item id", "value": raw})
            elif int(raw) not in ITEMS:
                self._json(404, {"error": "item not found", "id": int(raw)})
            else:
                self._json(200, {"id": int(raw), "name": ITEMS[int(raw)]})
        else:
            self._json(404, {"error": "not found", "path": parts.path})

    def do_POST(self):
        parts = urlsplit(self.path)
        payload, error = self._body()
        if error:
            self._json(400, {"error": error})
        elif parts.path == "/api/echo":
            self._json(200, {"echo": payload})
        elif parts.path == "/api/validate":
            errors = []
            if not isinstance(payload, dict):
                errors.append({"field": "", "message": "expected an object", "value": payload})
            else:
                for field, value in payload.items():
                    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9 _.-]{1,64}", value):
                        errors.append({"field": field, "message": "invalid value", "value": value})
            self._json(400 if errors else 200, {"valid": not errors, "errors": errors})
        else:
            self._json(404, {"error": "not found", "path": parts.path})

    def log_message(self, format, *args):  # quiet: the benchmark reads findings, not logs
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
