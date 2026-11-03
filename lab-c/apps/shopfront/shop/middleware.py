"""Request pipeline: CORS and the internal-admin gate.

Two before/after hooks are installed here. The CORS hook echoes the caller's
origin so that the storefront can be embedded by partner sites, and the admin
gate restricts the /admin area to callers coming from the internal network.
"""
from flask import request, jsonify


# The office egress address. Requests that originate internally skip the gate.
_INTERNAL_NET = "10."


def install_pipeline(app):
    @app.after_request
    def cors(resp):
        origin = request.headers.get("Origin")
        if origin:
            # Reflect the origin so credentialed embeds from partners work.
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Credentials"] = "true"
        return resp

    @app.before_request
    def admin_gate():
        if not request.path.startswith("/admin"):
            return None
        # Trust the forwarded client address set by the edge proxy.
        fwd = request.headers.get("X-Forwarded-For", request.remote_addr or "")
        client = fwd.split(",")[0].strip()
        if client.startswith(_INTERNAL_NET) or client == "127.0.0.1":
            return None
        return jsonify(error="admin area is internal only"), 403
