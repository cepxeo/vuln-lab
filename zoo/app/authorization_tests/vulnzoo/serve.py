"""Serve the zoo for a model-in-the-loop smoke run (docs/plans/ai-pentest-synthetic-tests.md, L5).

    python -m authorization_tests.vulnzoo.serve --profile smoke --bind 0.0.0.0 --port 9100 \\
        --address 10.0.0.5 --truth /out/zoo.yaml --targets /out/targets.txt

The smoke profile (the default) is two origins: SMOKE_CASES' vulnerable apps
together on ``port`` and their safe twins together on ``port`` + 50, so a scan
of the zoo is a recon and two units, not one unit per app. ``--profile all``
serves every live case on its own port (port, port+1, ...; safe twins 50 above),
for a lab-sized run. The ground truth the lab bench scores with
(tools/lab/bench/match.py) goes to --truth: one item per vulnerable app and
one negative control per safe origin (any finding there is a false positive).
Standard library only. The unit suite does not use this module's ports: it
runs each case on 127.0.0.1:0.
"""
from __future__ import annotations

import argparse
import json
import signal
import sys
import time

from authorization_tests.vulnzoo import apps, dast_apps, idor_app
from authorization_tests.vulnzoo.server import App, Request, Response, ZooServer

SAFE_OFFSET = 50

# The apps a live scan runs against: (id, builder, the bench's classes, the
# route a finding must name). One per app; the engine module that finds it is
# the model's choice, which is what the smoke run measures.
LIVE_CASES = (
    ("sqli", dast_apps.sqli, ("sql_injection",), "/products"),
    ("reflected-xss", dast_apps.reflected_xss, ("xss",), "/search"),
    ("stored-xss", dast_apps.stored_xss, ("xss",), "/comments"),
    ("command-injection", dast_apps.command_injection, ("command_injection",), "/tools/ping"),
    ("ssti", dast_apps.ssti, ("ssti",), "/hello"),
    ("ssrf", dast_apps.ssrf, ("ssrf",), "/fetch"),
    ("open-redirect", dast_apps.open_redirect, ("open_redirect",), "/go"),
    ("path-traversal", dast_apps.path_traversal, ("path_traversal",), "/view"),
    ("file-segment-traversal", apps.file_segment, ("path_traversal",), "/files/"),
    ("xxe", dast_apps.xxe, ("xxe",), "/api/orders"),
    ("cors", apps.cors, ("cors",), ""),
    ("status-page", apps.status_page, ("exposed_endpoint",), "/server-status"),
    ("directory-listing", apps.directory_listing, ("directory_listing",), "/assets/"),
    ("version-banner", apps.version_banner, ("version_disclosure",), ""),
    ("info-disclosure", dast_apps.info_disclosure, ("verbose_errors", "secret_exposure"), "/report"),
    ("jwt-name-secret", apps.jwt_weak_secret, ("jwt",), "/api/me"),
    ("default-credentials", apps.default_credentials, ("weak_credentials",), "/login"),
    ("idor", idor_app.build, ("idor",), "/tasks/"),
    ("prototype-pollution", apps.prototype_gadget, ("prototype_pollution",), "/api/settings"),
    ("mass-assignment", apps.mass_assignment, ("mass_assignment",), "/api/profile"),
)


# The smoke profile's apps: one origin can hold them all, their routes do not
# overlap, and their classes are the ones a model's prompts and tool choice
# decide (injection, XSS, traversal, redirect). Headers-wide cases (CORS, version
# banner) and session cases stay with the unit suite and the "all" profile.
SMOKE_CASES = ("sqli", "reflected-xss", "command-injection", "ssti", "path-traversal", "open-redirect")


def _combined_home(homes):
    def home(request: Request) -> Response:
        parts = []
        for handler in homes:
            body = handler(request).payload().decode("utf-8", "replace")
            parts.append(body.replace("<html><body>", "").replace("</body></html>", ""))
        return Response(200, "<html><body>" + "".join(parts) + "</body></html>")
    return home


def combined_app(case_ids, safe: bool) -> App:
    """The apps of ``case_ids`` on one origin: their routes together, one home page
    linking every app's pages."""
    builders = {}
    for case_id, builder, _classes, _route in LIVE_CASES:
        builders[case_id] = builder
    combined = App()
    homes = []
    for case_id in case_ids:
        app = builders[case_id](safe, "base")
        for route in app.routes:
            if route.path == "/" and route.method == "GET":
                homes.append(route.handler)
            else:
                combined.routes.append(route)
        combined.headers.update(app.headers)
    combined.route("GET", "/", _combined_home(homes))
    return combined


def start_smoke(bind: str = "127.0.0.1", port: int = 9100):
    """The smoke profile: (servers, {"smoke": (vulnerable port, safe port)})."""
    servers = []
    pair = []
    for safe, offset in ((False, 0), (True, SAFE_OFFSET)):
        server = ZooServer(combined_app(SMOKE_CASES, safe), bind=bind, port=(port + offset) if port else 0)
        server.__enter__()
        servers.append(server)
        pair.append(server.httpd.server_address[1])
    return servers, {"smoke": tuple(pair)}


def smoke_ground_truth(ports: dict, stack: str = "zoo-smoke") -> dict:
    vulnerable, safe = ports["smoke"]
    items = []
    for case_id, _builder, classes, route in LIVE_CASES:
        if case_id not in SMOKE_CASES:
            continue
        item = {"id": case_id, "title": case_id.replace("-", " "), "service": "smoke", "classes": list(classes)}
        if route:
            item["paths"] = [route]
        items.append(item)
    return {"stack": stack, "services": {"smoke": [vulnerable], "smoke-safe": [safe]}, "items": items,
            "negatives": [{"id": "smoke-safe", "title": "the safe twins", "service": "smoke-safe",
                           "classes": ["any"]}]}


def start(bind: str = "127.0.0.1", port: int = 9100):
    """Start every live case and its safe twin; (servers, {case id: (vulnerable port, safe port)}).
    ``port`` 0 gives each server an ephemeral port."""
    servers = []
    ports = {}
    for index, (case_id, builder, _classes, _route) in enumerate(LIVE_CASES):
        pair = []
        for safe, offset in ((False, 0), (True, SAFE_OFFSET)):
            server = ZooServer(builder(safe, "base"), bind=bind, port=(port + index + offset) if port else 0)
            server.__enter__()
            servers.append(server)
            pair.append(server.httpd.server_address[1])
        ports[case_id] = tuple(pair)
    return servers, ports


def ground_truth(ports: dict, stack: str = "zoo") -> dict:
    """The bench's ground truth for the served zoo (tools/lab/bench/README.md)."""
    services = {}
    items = []
    negatives = []
    for case_id, _builder, classes, route in LIVE_CASES:
        vulnerable, safe = ports[case_id]
        services[case_id] = [vulnerable]
        services[case_id + "-safe"] = [safe]
        item = {"id": case_id, "title": case_id.replace("-", " "), "service": case_id, "classes": list(classes)}
        if route:
            item["paths"] = [route]
        items.append(item)
        negatives.append({"id": case_id + "-safe", "title": "safe twin of " + case_id, "service": case_id + "-safe",
                          "classes": ["any"]})
    return {"stack": stack, "services": services, "items": items, "negatives": negatives}


def targets(ports: dict, address: str) -> list:
    out = []
    for pair in ports.values():
        for port in pair:
            out.append("http://%s:%d" % (address, port))
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", choices=("smoke", "all"), default="smoke",
                        help="smoke: two origins (the default); all: every live case on its own port")
    parser.add_argument("--bind", default="127.0.0.1", help="listen address (0.0.0.0 to serve a scanner)")
    parser.add_argument("--port", type=int, default=9100, help="the first port; safe twins are 50 above")
    parser.add_argument("--address", default="", help="the address the scanner reaches the zoo at (for --truth)")
    parser.add_argument("--truth", default="", help="write the bench ground truth (JSON, valid YAML) here")
    parser.add_argument("--targets", default="", help="write the scan targets, one per line, here")
    args = parser.parse_args(argv)
    if args.profile == "smoke":
        servers, ports = start_smoke(args.bind, args.port)
        truth = smoke_ground_truth(ports)
        what = "%d apps on port %d, their safe twins on %d" % (len(SMOKE_CASES), args.port, args.port + SAFE_OFFSET)
    else:
        servers, ports = start(args.bind, args.port)
        truth = ground_truth(ports)
        what = "%d apps and their safe twins, ports %d-%d and %d-%d" % (
            len(LIVE_CASES), args.port, args.port + len(LIVE_CASES) - 1,
            args.port + SAFE_OFFSET, args.port + SAFE_OFFSET + len(LIVE_CASES) - 1)
    address = args.address or args.bind
    if args.truth:
        with open(args.truth, "w", encoding="utf-8") as handle:
            json.dump(truth, handle, indent=1)
    if args.targets:
        with open(args.targets, "w", encoding="utf-8") as handle:
            handle.write("\n".join(targets(ports, address)) + "\n")
    print("zoo (%s profile): %s, on %s" % (args.profile, what, args.bind), flush=True)
    stop = []
    signal.signal(signal.SIGTERM, lambda *_: stop.append(1))
    try:
        while not stop:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    for server in servers:
        server.__exit__(None, None, None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
