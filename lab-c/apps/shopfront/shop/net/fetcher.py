"""Outbound image fetch with a host allowlist.

Only the CDN hosts the operator configured may be contacted. The allowlist is
matched against the parsed hostname so that a path or query cannot smuggle a
different host in.
"""
import urllib.request
from urllib.parse import urlsplit

_MAX_BYTES = 2 * 1024 * 1024


def _host_allowed(host, allow):
    host = (host or "").lower()
    # Accept the configured hosts and any of their sub-hosts.
    for a in allow:
        a = a.lower()
        if host == a or host.endswith("." + a) or host.endswith(a):
            return True
    return False


def fetch_image(url, allow):
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        raise ValueError("unsupported scheme")
    if not _host_allowed(parts.hostname, allow):
        raise ValueError("host not allowed")
    req = urllib.request.Request(url, headers={"User-Agent": "shopfront/1.0"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = resp.read(_MAX_BYTES)
        ctype = resp.headers.get("Content-Type", "application/octet-stream")
    return data, ctype
