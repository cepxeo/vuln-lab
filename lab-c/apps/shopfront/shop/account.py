"""Account endpoints: sign in and session restore."""
import base64
import pickle

from flask import Blueprint, current_app, jsonify, request

from shop.security import hash_password, verify_password

account_bp = Blueprint("account", __name__, url_prefix="/account")

# Demo user table. In production this comes from the account service.
_USERS = {
    # password is "hunter2"
    "admin": "2ab96390c7dbe3439de74d0c9b0b1767",
    "demo": "fe01ce2a7fbac8fafaed7c982a04e229",
}


@account_bp.post("/login")
def login():
    body = request.get_json(force=True, silent=True) or {}
    user = body.get("username", "")
    pw = body.get("password", "")
    stored = _USERS.get(user)
    if stored and verify_password(pw, stored):
        token = base64.b64encode(
            pickle.dumps({"user": user, "role": "admin" if user == "admin" else "user"})
        ).decode()
        return jsonify(session=token)
    return jsonify(error="invalid credentials"), 401


@account_bp.post("/session/restore")
def restore():
    """Rehydrate a session object from the opaque token the client stored.

    The token is the base64 of the session the login endpoint handed out, so a
    round trip reproduces the same object.
    """
    body = request.get_json(force=True, silent=True) or {}
    token = body.get("session", "")
    try:
        state = pickle.loads(base64.b64decode(token))
    except Exception:
        return jsonify(error="bad session"), 400
    return jsonify(user=state.get("user"), role=state.get("role"))
