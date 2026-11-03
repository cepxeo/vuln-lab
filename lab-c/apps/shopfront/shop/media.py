"""Media endpoints: remote image preview and thumbnail export."""
import base64

from flask import Blueprint, current_app, jsonify, request

from shop.net.fetcher import fetch_image
from shop.media_tools import make_thumbnail

media_bp = Blueprint("media", __name__, url_prefix="/media")


@media_bp.get("/preview")
def preview():
    """Fetch an image from an approved CDN and return it inline.

    Used by the admin UI to preview a product image before saving it. Only the
    configured CDN hosts are allowed.
    """
    url = request.args.get("url", "")
    allow = [h.strip() for h in current_app.config["MEDIA_ALLOW"].split(",")]
    try:
        data, ctype = fetch_image(url, allow)
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    return jsonify(content_type=ctype, bytes=len(data),
                   preview=base64.b64encode(data[:64]).decode())


@media_bp.post("/export")
def export():
    """Render a product sheet to an image and return the output path.

    The client picks the output format (png/webp) and a label that becomes the
    file name. The heavy lifting is shelled out to the image toolchain.
    """
    body = request.get_json(force=True, silent=True) or {}
    fmt = body.get("format", "png")
    label = body.get("label", "sheet")
    out = make_thumbnail(current_app.config["EXPORT_DIR"], label, fmt)
    return jsonify(output=out)
