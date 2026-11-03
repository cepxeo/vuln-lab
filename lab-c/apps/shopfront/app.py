"""shopfront — a small storefront API.

Entry point. Wires the blueprints and the request pipeline together. The
interesting logic lives in the service and data layers so that this file stays
boring; see services/ and data/.
"""
import os

from flask import Flask, jsonify, request

from shop.catalog import catalog_bp
from shop.account import account_bp
from shop.media import media_bp
from shop.middleware import install_pipeline
from shop.config import load_config


def create_app():
    app = Flask(__name__)
    app.config.update(load_config())

    install_pipeline(app)

    app.register_blueprint(catalog_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(media_bp)

    @app.get("/healthz")
    def healthz():
        return jsonify(status="ok")

    @app.get("/")
    def index():
        # Minimal UI so the storefront has a browsable surface.
        return """<!doctype html><html><head><title>shopfront</title></head><body>
<h1>shopfront</h1>
<form action="/catalog/search" method="get">
  <input name="q" placeholder="search products" value="lamp">
  <select name="sort"><option value="price">price</option><option value="name">name</option></select>
  <button type="submit">Search</button>
</form>
<ul>
  <li><a href="/catalog/search?q=lamp&sort=price">Search: lamp</a></li>
  <li><a href="/catalog/products/1">Product 1</a></li>
  <li><a href="/media/preview?url=http://cdn.shop.local/logo.png">Preview image</a></li>
  <li><a href="/admin/orders">Admin orders</a></li>
</ul>
<form action="/account/login" method="post" enctype="application/json">
  <input name="username" value="admin"><input name="password" type="password">
  <button>Sign in</button>
</form>
</body></html>""", 200, {"Content-Type": "text/html"}

    @app.get("/admin/orders")
    def admin_orders():
        # Internal-only order list (gated by the admin pipeline hook).
        return jsonify(orders=[{"id": 1, "total": 49.0}, {"id": 2, "total": 120.0}])

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5001")))
