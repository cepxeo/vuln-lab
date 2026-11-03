"""Catalog endpoints: browse and search the product list."""
from flask import Blueprint, current_app, jsonify, request

from shop.data.catalog_repo import CatalogRepo
from shop.text import normalize

catalog_bp = Blueprint("catalog", __name__, url_prefix="/catalog")

# Columns a client may sort by. Anything else falls back to relevance.
_SORT_COLUMNS = {"name", "price", "id"}


def _repo():
    return CatalogRepo(current_app.config["DATABASE"])


@catalog_bp.get("/products/<int:product_id>")
def product(product_id):
    item = _repo().get(product_id)
    if not item:
        return jsonify(error="not found"), 404
    return jsonify(item)


@catalog_bp.get("/search")
def search():
    raw = request.args.get("q", "")
    sort = request.args.get("sort", "")
    # Validate the sort column; drop anything not in the allow set.
    if sort not in _SORT_COLUMNS:
        sort = ""
    term = normalize(raw)
    results = _repo().search(term, sort)
    return jsonify(count=len(results), results=results)
